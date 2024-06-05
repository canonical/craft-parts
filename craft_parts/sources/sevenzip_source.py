# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017 Tim Süberkrüb
# Copyright 2018-2022 Canonical Ltd.
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

"""Implement the 7zip file source handler."""

import os
from pathlib import Path
from typing import List, Optional

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler


class SevenzipSource(FileSourceHandler):
    """The zip file source handler."""

    def __init__(  # noqa: PLR0913
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_tag: Optional[str] = None,
        source_commit: Optional[str] = None,
        source_branch: Optional[str] = None,
        source_depth: Optional[int] = None,
        source_checksum: Optional[str] = None,
        source_submodules: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_branch=source_branch,
            source_commit=source_commit,
            source_checksum=source_checksum,
            source_depth=source_depth,
            source_submodules=source_submodules,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
            command="7zip",
        )
        if source_tag:
            raise errors.InvalidSourceOption(source_type="7z", option="source-tag")

        if source_commit:
            raise errors.InvalidSourceOption(source_type="7z", option="source-commit")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="7z", option="source-branch")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="7z", option="source-depth")

    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Optional[Path] = None,
    ) -> None:
        """Extract 7z file contents to the part source dir."""
        if src:
            sevenzip_file = src
        else:
            sevenzip_file = Path(self.part_src_dir, os.path.basename(self.source))

        sevenzip_file = sevenzip_file.expanduser().resolve()
        self._run_output(["7z", "x", f"-o{dst}", str(sevenzip_file)])

        if not keep:
            os.remove(sevenzip_file)
