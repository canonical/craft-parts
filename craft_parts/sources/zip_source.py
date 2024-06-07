# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2022 Canonical Ltd.
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

"""Implement the zip file source handler."""

import os
import zipfile
from pathlib import Path

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler


class ZipSource(FileSourceHandler):
    """The zip file source handler."""

    # pylint: disable=too-many-arguments
    def __init__(  # noqa: PLR0913
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_tag: str | None = None,
        source_branch: str | None = None,
        source_commit: str | None = None,
        source_depth: int | None = None,
        source_checksum: str | None = None,
        source_submodules: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_branch=source_branch,
            source_commit=source_commit,
            source_depth=source_depth,
            source_checksum=source_checksum,
            source_submodules=source_submodules,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )
        if source_tag:
            raise errors.InvalidSourceOption(source_type="zip", option="source-tag")

        if source_commit:
            raise errors.InvalidSourceOption(source_type="zip", option="source-commit")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="zip", option="source-branch")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="zip", option="source-depth")

    # pylint: enable=too-many-arguments

    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Extract zip file contents to the part source dir."""
        zip_file = src if src else self.part_src_dir / os.path.basename(self.source)

        # Workaround for: https://bugs.python.org/issue15795
        with zipfile.ZipFile(zip_file, "r") as zipf:
            for info in zipf.infolist():
                extracted_file = zipf.extract(info.filename, path=dst)

                # Extract the mode from the file. Note that external_attr is
                # a four-byte value, where the high two bytes represent UNIX
                # permissions and file type bits, and the low two bytes contain
                # MS-DOS FAT file attributes. Keep the mode to permissions
                # only-- no sticky bit, uid bit, or gid bit.
                mode = info.external_attr >> 16 & 0x1FF

                # If the zip file was created on a non-unix system, it's
                # possible for the mode to end up being zero. That makes it
                # pretty useless, so ignore it if so.
                if mode:
                    os.chmod(extracted_file, mode)

        if not keep:
            os.remove(zip_file)
