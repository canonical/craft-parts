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
from typing import List, Optional

from craft_parts.dirs import ProjectDirs

from .base import FileSourceHandler


class ZipSource(FileSourceHandler):
    """The zip file source handler."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        source_checksum: Optional[str] = None,
        project_dirs: Optional[ProjectDirs] = None,
        ignore_patterns: Optional[List[str]] = None,
        **invalid_options: None,
    ):
        self._check_invalid_options("zip", invalid_options)
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_checksum=source_checksum,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )

    # pylint: enable=too-many-arguments

    def provision(
        self,
        dst: Path,
        keep: bool = False,
        src: Optional[Path] = None,
    ) -> None:
        """Extract zip file contents to the part source dir."""
        if src:
            zip_file = src
        else:
            zip_file = self.part_src_dir / os.path.basename(self.source)

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
