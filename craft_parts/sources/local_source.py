# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021,2024 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The local source handler and helpers."""

import functools
import logging
import os
import pathlib
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal

import pydantic
from typing_extensions import override

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import file_utils

from . import errors
from .base import (
    BaseSourceModel,
    SourceHandler,
    get_json_extra_schema,
    get_model_config,
)

logger = logging.getLogger(__name__)


class LocalSourceModel(BaseSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for a generic local source."""

    model_config = get_model_config(get_json_extra_schema(r"^\./?"))
    source_type: Literal["local"] = "local"
    source: Annotated[  # type: ignore[assignment]
        pathlib.Path,
        pydantic.AfterValidator(lambda source: pathlib.Path(source)),  # noqa: PLW0108 - ruff suggests that the lambda is unnecessary, but pydantic breaks without it.
    ]


class LocalSource(SourceHandler):
    """The local source handler."""

    source_model = LocalSourceModel

    def __init__(
        self,
        *args: Any,
        project_dirs: ProjectDirs,
        copy_function: Callable[..., None] = file_utils.link_or_copy,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, project_dirs=project_dirs, **kwargs)
        self.source_abspath = Path(self.source).absolute()
        self.copy_function = copy_function

        _source_resolved = self.source_abspath.resolve()
        _work_dir_resolved = self._dirs.work_dir.resolve()

        _nested_craft_dirs: frozenset[Path] = frozenset()

        _craft_output_dirs = [
            p
            for p in [
                self._dirs.parts_dir,
                self._dirs.stage_dir,
                self._dirs.prime_dir,
                self._dirs.overlay_dir,
                self._dirs.partition_dir,
            ]
            if p is not None
        ]

        if _source_resolved == _work_dir_resolved:
            # Fast path: source IS work_dir — output dirs are direct children,
            # exclude by name.
            self._ignore_patterns.extend(p.name for p in _craft_output_dirs)
        elif _work_dir_resolved.is_relative_to(_source_resolved):
            if self._dirs.root_dir is not None:
                # root_dir rewrite: work_dir is a source subdirectory containing
                # real source files alongside craft output dirs.  Exclude only
                # the specific craft output dirs by absolute path so the source
                # files in work_dir are still staged.
                _nested_craft_dirs = frozenset(p.resolve() for p in _craft_output_dirs)
            else:
                # Traditional case: work_dir is nested inside source and is
                # treated as a craft-only directory.  Exclude the entire subtree
                # via the first path component.
                rel = _work_dir_resolved.relative_to(_source_resolved)
                self._ignore_patterns.append(rel.parts[0])

        logger.debug("ignore patterns: %r", self._ignore_patterns)

        self._ignore = functools.partial(
            _ignore, self.source_abspath, Path.cwd(), self._ignore_patterns
        )

        if _nested_craft_dirs:
            _base = self._ignore

            def _ignore_with_nested_craft_dirs(
                directory: Path | str,
                files: list[str],
                also_ignore: list[str] | None = None,
                *,
                _craft: frozenset[Path] = _nested_craft_dirs,
                _base_fn: functools.partial[list[str]] = _base,
            ) -> list[str]:
                excluded = set(_base_fn(directory, files, also_ignore=also_ignore) or [])
                for name in files:
                    if Path(directory, name).resolve() in _craft:
                        excluded.add(name)
                return list(excluded)

            self._ignore = _ignore_with_nested_craft_dirs
        self._updated_files: set[str] = set()
        self._updated_directories: set[str] = set()

    @override
    def pull(self) -> None:
        """Retrieve the local source files."""
        if not Path(self.source_abspath).exists():
            raise errors.SourceNotFound(self.source)

        file_utils.link_or_copy_tree(
            self.source_abspath,
            self.part_src_dir,
            ignore=self._ignore,
            copy_function=self.copy_function,
        )

    @override
    def check_if_outdated(
        self, target: str, *, ignore_files: list[str] | None = None
    ) -> bool:
        """Check if pulled sources have changed since target was created.

        :param target: Path to target file.
        :param ignore_files: Files excluded from verification.

        :return: Whether the sources are outdated.
        """
        if not ignore_files:
            ignore_files = []

        try:
            target_mtime = os.lstat(target).st_mtime
        except FileNotFoundError:
            return False

        self._updated_files = set()
        self._updated_directories = set()

        for root, directories, files in os.walk(self.source_abspath, topdown=True):
            ignored = set(
                self._ignore(Path(root), directories + files, also_ignore=ignore_files)
            )
            if ignored:
                # Prune our search appropriately given an ignore list, i.e.
                # don't walk into directories that are ignored.
                directories[:] = [d for d in directories if d not in ignored]

            for file_name in set(files) - ignored:
                path = Path(root, file_name)
                if os.lstat(path).st_mtime >= target_mtime:
                    self._updated_files.add(os.path.relpath(path, self.source))

            directories_to_remove: list[str] = []
            for directory in directories:
                path = Path(root, directory)
                if os.lstat(path).st_mtime >= target_mtime:
                    # Don't descend into this directory-- we'll just copy it
                    # entirely.
                    directories_to_remove.append(directory)

                    # os.walk will include symlinks to directories here, but we
                    # want to treat those as files
                    relpath = os.path.relpath(path, self.source)
                    if path.is_symlink():
                        self._updated_files.add(relpath)
                    else:
                        self._updated_directories.add(relpath)
            for directory in directories_to_remove:
                directories.remove(directory)

        logger.debug("updated files: %r", self._updated_files)
        logger.debug("updated directories: %r", self._updated_directories)

        return len(self._updated_files) > 0 or len(self._updated_directories) > 0

    @override
    def get_outdated_files(self) -> tuple[list[str], list[str]]:
        """Obtain lists of outdated files and directories.

        :return: The lists of outdated files and directories.

        :raise errors.SourceUpdateUnsupported: If the source handler can't check if
            files are outdated.
        """
        return (sorted(self._updated_files), sorted(self._updated_directories))

    @override
    def update(self) -> None:
        """Update pulled source.

        Call method :meth:`check_if_outdated` before updating to populate the
        lists of files and directories to copy.
        """
        # First, copy the directories
        for directory in self._updated_directories:
            file_utils.link_or_copy_tree(
                Path(self.source, directory),
                Path(self.part_src_dir, directory),
                ignore=self._ignore,
                copy_function=self.copy_function,
            )

        # Now, copy files
        for file_path in self._updated_files:
            self.copy_function(
                Path(self.source, file_path),
                Path(self.part_src_dir, file_path),
            )


def _ignore(
    source: Path,
    current_directory: Path,
    patterns: list[str],
    directory: Path | str,
    _files: Any,  # noqa: ANN401
    also_ignore: list[str] | None = None,
) -> list[str]:
    """Build a list of files to ignore based on the given patterns."""
    ignored: list[str] = []
    directory = Path(directory)
    if directory in (source, current_directory):
        for pattern in patterns + (also_ignore or []):
            files = [f.name for f in directory.glob(pattern)]
            if files:
                ignored += files

    return ignored
