# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The local source handler and helpers."""

import functools
import glob
import os
from typing import List, Optional

from craft_parts.utils import file_utils

from .base import SourceHandler

# TODO: change file operations to use pathlib


class LocalSource(SourceHandler):
    """The local source handler."""

    def __init__(self, *args, copy_function=file_utils.link_or_copy, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_abspath = os.path.abspath(self.source)
        self.copy_function = copy_function

        ignore_patterns = [
            self._dirs.parts_dir.name,
            self._dirs.stage_dir.name,
            self._dirs.prime_dir.name,
            "*.snap",  # FIXME: this should be specified by the application
        ]
        self._ignore = functools.partial(
            _ignore, self.source_abspath, os.getcwd(), ignore_patterns
        )
        self._updated_files = set()
        self._updated_directories = set()

    def pull(self):
        """Retrieve the local source files."""
        file_utils.link_or_copy_tree(
            self.source_abspath,
            self.part_src_dir,
            ignore=self._ignore,
            copy_function=self.copy_function,
        )

    def check_if_outdated(
        self, target: str, *, ignore_files: Optional[List[str]] = None
    ) -> bool:
        """Check if pulled sources have changed since target was created.

        :param target: Path to target file.
        :param ignore_files: Files excluded from verification.

        :return: Whether the sources are outdated.
        """
        try:
            target_mtime = os.lstat(target).st_mtime
        except FileNotFoundError:
            return False

        self._updated_files = set()
        self._updated_directories = set()

        for (root, directories, files) in os.walk(self.source_abspath, topdown=True):
            ignored = set(
                self._ignore(root, directories + files, also_ignore=ignore_files)
            )
            if ignored:
                # Prune our search appropriately given an ignore list, i.e.
                # don't walk into directories that are ignored.
                directories[:] = [d for d in directories if d not in ignored]

            for file_name in set(files) - ignored:
                path = os.path.join(root, file_name)
                if os.lstat(path).st_mtime >= target_mtime:
                    self._updated_files.add(os.path.relpath(path, self.source))

            for directory in directories:
                path = os.path.join(root, directory)
                if os.lstat(path).st_mtime >= target_mtime:
                    # Don't descend into this directory-- we'll just copy it
                    # entirely.
                    directories.remove(directory)

                    # os.walk will include symlinks to directories here, but we
                    # want to treat those as files
                    relpath = os.path.relpath(path, self.source)
                    if os.path.islink(path):
                        self._updated_files.add(relpath)
                    else:
                        self._updated_directories.add(relpath)

        return len(self._updated_files) > 0 or len(self._updated_directories) > 0

    def update(self):
        """Update pulled source."""
        # First, copy the directories
        for directory in self._updated_directories:
            file_utils.link_or_copy_tree(
                os.path.join(self.source, directory),
                os.path.join(self.part_src_dir, directory),
                ignore=self._ignore,
                copy_function=self.copy_function,
            )

        # Now, copy files
        for file_path in self._updated_files:
            self.copy_function(
                os.path.join(self.source, file_path),
                os.path.join(self.part_src_dir, file_path),
            )


def _ignore(
    source: str,
    current_directory: str,
    patterns: List[str],
    directory,
    files,
    also_ignore: List[str] = None,
) -> List[str]:
    if also_ignore:
        patterns.extend(also_ignore)

    ignored = []
    if directory in (source, current_directory):
        for pattern in patterns:
            files = glob.glob(os.path.join(directory, pattern))
            if files:
                files = [os.path.basename(f) for f in files]
                ignored += files

    return ignored
