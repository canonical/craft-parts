# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""Implement the plain file source handler."""

from pathlib import Path
from typing import List, Optional

from overrides import overrides

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler


class FileSource(FileSourceHandler):
    """The plain file source handler."""

    # pylint: disable-next=too-many-arguments
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
        source_submodules: Optional[List[str]] = None,
        source_checksum: Optional[str] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_commit=source_commit,
            source_tag=source_tag,
            source_branch=source_branch,
            source_depth=source_depth,
            source_checksum=source_checksum,
            source_submodules=source_submodules,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )

        if source_commit:
            raise errors.InvalidSourceOption(source_type="file", option="source-commit")

        if source_tag:
            raise errors.InvalidSourceOption(source_type="file", option="source-tag")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="file", option="source-depth")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="file", option="source-branch")

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Optional[Path] = None,
    ) -> None:
        """Process the source file to extract its payload."""
        # No payload to extract
