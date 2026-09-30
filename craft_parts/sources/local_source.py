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

import contextlib
import functools
import logging
import os
import pathlib
import shutil
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

# File written to the source cache after a pull to record the set of source
# entries at that point in time. Used by check_if_outdated() to detect files
# and directories that were deleted from the source since the last pull.
_SOURCE_MANIFEST_FILENAME = ".craft-parts-source-manifest"


class LocalSourceModel(BaseSourceModel, frozen=True):
    """Pydantic model for a generic local source."""

    model_config = get_model_config(get_json_extra_schema(r"^\./?"))
    source_type: Literal["local"] = "local"
    source: Annotated[
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
        self._manifest_path = Path(self._cache_dir) / _SOURCE_MANIFEST_FILENAME

        if self._dirs.work_dir.resolve() == Path(self.source_abspath):
            # ignore parts/stage/dir if source dir matches workdir
            self._ignore_patterns.append(self._dirs.parts_dir.name)
            self._ignore_patterns.append(self._dirs.stage_dir.name)
            self._ignore_patterns.append(self._dirs.prime_dir.name)
            self._ignore_patterns.append(self._dirs.overlay_dir.name)
            if self._dirs.partition_dir:
                self._ignore_patterns.append(self._dirs.partition_dir.name)
        else:
            # otherwise check if work_dir inside source dir
            with contextlib.suppress(ValueError):
                rel_work_dir = self._dirs.work_dir.relative_to(self.source_abspath)
                # deep workdirs will be cut at the first component
                self._ignore_patterns.append(rel_work_dir.parts[0])

        logger.debug("ignore patterns: %r", self._ignore_patterns)

        self._ignore = functools.partial(
            _ignore, self.source_abspath, Path.cwd(), self._ignore_patterns
        )
        self._updated_files: set[str] = set()
        self._updated_directories: set[str] = set()
        self._deleted_files: set[str] = set()
        self._deleted_directories: set[str] = set()

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

        _write_source_manifest(
            self._manifest_path,
            _collect_source_entries(self.source_abspath, self._ignore),
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
        self._deleted_files = set()
        self._deleted_directories = set()

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

        self._detect_deletions(ignore_files)

        logger.debug("deleted files: %r", self._deleted_files)
        logger.debug("deleted directories: %r", self._deleted_directories)

        return (
            len(self._updated_files) > 0
            or len(self._updated_directories) > 0
            or len(self._deleted_files) > 0
            or len(self._deleted_directories) > 0
        )

    def _detect_deletions(self, ignore_files: list[str]) -> None:
        """Detect files/directories deleted from the source since the last pull.

        Compares the current source against the stored manifest.  We
        intentionally compare source-vs-manifest (not destination-vs-source)
        so that files added to part_src_dir by later lifecycle steps (e.g. build
        artifacts in part_build_dir when LocalSource is used for build updates)
        are never incorrectly treated as deletions.
        """
        prev_entries = _read_source_manifest(self._manifest_path)
        if prev_entries is None:
            return

        current_entries = _collect_source_entries(
            self.source_abspath, self._ignore, also_ignore=ignore_files
        )
        deleted = prev_entries - current_entries

        # Classify each deleted entry as a file or a directory based on
        # what is currently present in the destination (part_src_dir).
        deleted_dirs: set[str] = set()
        for rel_path in deleted:
            dest_path = Path(self.part_src_dir) / rel_path
            if not dest_path.is_symlink() and dest_path.is_dir():
                deleted_dirs.add(rel_path)
            else:
                self._deleted_files.add(rel_path)

        # Filter out files that are inside deleted directories - the whole
        # directory tree will be removed by shutil.rmtree in update().
        self._deleted_files = {
            f
            for f in self._deleted_files
            if not any(f == d or f.startswith(d + os.sep) for d in deleted_dirs)
        }
        self._deleted_directories = deleted_dirs

        for rel_path in current_entries:
            source_path = self.source_abspath / rel_path
            dest_path = Path(self.part_src_dir) / rel_path
            source_is_dir = source_path.is_dir() and not source_path.is_symlink()
            dest_is_dir = dest_path.is_dir() and not dest_path.is_symlink()
            if source_is_dir != dest_is_dir and os.path.lexists(dest_path):
                if dest_is_dir:
                    self._deleted_directories.add(rel_path)
                else:
                    self._deleted_files.add(rel_path)

        ignored = set(ignore_files)
        self._deleted_files = {
            path
            for path in self._deleted_files
            if not any(
                path == item or path.startswith(item + os.sep) for item in ignored
            )
        }
        self._deleted_directories = {
            path
            for path in self._deleted_directories
            if not any(
                path == item or path.startswith(item + os.sep) for item in ignored
            )
        }

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
        # Remove stale paths before copying replacements.
        for directory in sorted(self._deleted_directories, reverse=True):
            dest_path = os.path.join(self.part_src_dir, directory)  # noqa: PTH118
            if os.path.islink(dest_path):  # noqa: PTH114
                os.remove(dest_path)  # noqa: PTH107
            elif os.path.isdir(dest_path):  # noqa: PTH112
                shutil.rmtree(dest_path)

        for file_path in self._deleted_files:
            dest_path = os.path.join(self.part_src_dir, file_path)  # noqa: PTH118
            if os.path.lexists(dest_path):
                os.remove(dest_path)  # noqa: PTH107

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

        # Refresh the manifest only if one already exists (i.e. pull() was
        # previously called for this source→destination pair).  Skipping this
        # when no manifest is present avoids inadvertently creating a manifest
        # for uses of LocalSource where pull() is never called (e.g. the
        # src→build update in _update_build), which would cause build artifacts
        # to be misidentified as deleted source files on the next check.
        if self._manifest_path.exists():
            _write_source_manifest(
                self._manifest_path,
                _collect_source_entries(self.source_abspath, self._ignore),
            )


def _collect_source_entries(
    source: Path,
    ignore_fn: Callable[..., list[str]],
    *,
    also_ignore: list[str] | None = None,
) -> set[str]:
    """Walk *source* and return relative paths of all entries (with ignore).

    Both regular files and directories are included so that the manifest can
    detect directory-level deletions as well as individual file deletions.
    Symlinks to directories are included as entries but are not descended into
    (matching the behaviour of :func:`~craft_parts.utils.file_utils.link_or_copy_tree`).
    """
    entries: set[str] = set()
    for root, directories, file_names in os.walk(source, topdown=True):
        ignored = set(
            ignore_fn(root, directories + file_names, also_ignore=also_ignore)
        )
        if ignored:
            directories[:] = [d for d in directories if d not in ignored]

        for file_name in set(file_names) - ignored:
            path = Path(root) / file_name
            entries.add(os.path.relpath(path, source))

        for directory in list(directories):
            path = Path(root) / directory
            entries.add(os.path.relpath(path, source))
            if os.path.islink(path):  # noqa: PTH114
                # Treat dir-symlinks as opaque entries; do not descend.
                directories.remove(directory)

    return entries


def _read_source_manifest(manifest_path: Path) -> set[str] | None:
    """Return the set of source entries recorded at the last pull, or None.

    Returns ``None`` when no manifest exists (e.g. after a clean or before
    the first pull with manifest support).
    """
    if not manifest_path.is_file():
        return None
    content = manifest_path.read_text().strip()
    return set(content.splitlines()) if content else set()


def _write_source_manifest(manifest_path: Path, entries: set[str]) -> None:
    """Write the source entry manifest to the cache."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("\n".join(sorted(entries)) + "\n")


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
