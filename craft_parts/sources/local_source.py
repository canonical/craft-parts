# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

import contextlib
import functools
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from overrides import overrides

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import file_utils

from . import errors
from .base import SourceHandler

logger = logging.getLogger(__name__)

# TODO: change file operations to use pathlib


class LocalSource(SourceHandler):
    """The local source handler."""

    def __init__(
        self,
        *args: Any,  # noqa: ANN401
        project_dirs: ProjectDirs,
        copy_function: Callable[..., None] = file_utils.link_or_copy,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(*args, project_dirs=project_dirs, **kwargs)
        if not isinstance(self.source, Path):
            raise errors.InvalidSourceType(str(self.source))
        self.source_abspath = self.source.resolve()
        self.copy_function = copy_function

        if self._dirs.work_dir.resolve() == Path(self.source_abspath):
            # ignore parts/stage/dir if source dir matches workdir
            self._ignore_patterns.append(self._dirs.parts_dir.name)
            self._ignore_patterns.append(self._dirs.stage_dir.name)
            self._ignore_patterns.append(self._dirs.prime_dir.name)
        else:
            # otherwise check if work_dir inside source dir
            with contextlib.suppress(ValueError):
                rel_work_dir = self._dirs.work_dir.relative_to(self.source_abspath)
                # deep workdirs will be cut at the first component
                self._ignore_patterns.append(rel_work_dir.parts[0])

        logger.debug("ignore patterns: %r", self._ignore_patterns)

        self._ignore = functools.partial(
            _ignore, str(self.source_abspath), str(Path.cwd()), self._ignore_patterns
        )
        self._updated_files: set[str] = set()
        self._updated_directories: set[str] = set()

    @overrides
    def pull(self) -> None:
        """Retrieve the local source files."""
        if not Path(self.source_abspath).exists():
            raise errors.SourceNotFound(str(self.source))

        file_utils.link_or_copy_tree(
            self.source_abspath,
            self.part_src_dir,
            ignore=self._ignore,
            copy_function=self.copy_function,
        )

    @overrides
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
                self._ignore(root, directories + files, also_ignore=ignore_files)
            )
            if ignored:
                # Prune our search appropriately given an ignore list, i.e.
                # don't walk into directories that are ignored.
                directories[:] = [d for d in directories if d not in ignored]

            for file_name in set(files) - ignored:
                path = Path(root) / file_name
                if os.lstat(path).st_mtime >= target_mtime:
                    self._updated_files.add(os.path.relpath(path, self.source))

            directories_to_remove = []
            for directory in directories:
                path = Path(root) / directory
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

    @overrides
    def get_outdated_files(self) -> tuple[list[str], list[str]]:
        """Obtain lists of outdated files and directories.

        :return: The lists of outdated files and directories.

        :raise errors.SourceUpdateUnsupported: If the source handler can't check if
            files are outdated.
        """
        return (sorted(self._updated_files), sorted(self._updated_directories))

    @overrides
    def update(self) -> None:
        """Update pulled source.

        Call method :meth:`check_if_outdated` before updating to populate the
        lists of files and directories to copy.
        """
        if not isinstance(self.source, Path):
            raise errors.InvalidSourceType(str(self.source))

        # First, copy the directories
        for directory in self._updated_directories:
            file_utils.link_or_copy_tree(
                self.source / directory,
                self.part_src_dir / directory,
                ignore=self._ignore,
                copy_function=self.copy_function,
            )

        # Now, copy files
        for file_path in self._updated_files:
            self.copy_function(
                self.source / file_path,
                self.part_src_dir / file_path,
            )


def _ignore(
    source: str,
    current_directory: str,
    patterns: list[str],
    directory: str,
    _files: Any,  # noqa: ANN401
    also_ignore: list[str] | None = None,
) -> list[str]:
    """Build a list of files to ignore based on the given patterns."""
    ignored: list[str] = []
    if directory in (source, current_directory):
        for pattern in patterns + (also_ignore or []):
            matched_files = Path(directory).rglob(pattern)
            if matched_files:
                files = [f.name for f in matched_files]
                ignored += files

    return ignored
