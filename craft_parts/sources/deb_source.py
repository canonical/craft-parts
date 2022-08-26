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

"""The deb source handler."""

import logging
import os
from pathlib import Path
from typing import List, Optional

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import deb_utils

from . import errors
from .base import FileSourceHandler

logger = logging.getLogger(__name__)


class DebSource(FileSourceHandler):
    """The "deb" file source handler."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        source_tag: Optional[str] = None,
        source_commit: Optional[str] = None,
        source_branch: Optional[str] = None,
        source_checksum: Optional[str] = None,
        source_submodules: Optional[List[str]] = None,
        source_depth: Optional[int] = None,
        project_dirs: Optional[ProjectDirs] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_branch=source_branch,
            source_commit=source_commit,
            source_checksum=source_checksum,
            source_submodules=source_submodules,
            source_depth=source_depth,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )

        if source_tag:
            raise errors.InvalidSourceOption(source_type="deb", option="source-tag")

        if source_commit:
            raise errors.InvalidSourceOption(source_type="deb", option="source-commit")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="deb", option="source-branch")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="deb", option="source-depth")

    # pylint: enable=too-many-arguments

    def provision(
        self,
        dst: Path,
        keep: bool = False,
        src: Optional[Path] = None,
    ):
        """Extract deb file contents to the part source dir."""
        if src:
            deb_file = src
        else:
            deb_file = self.part_src_dir / os.path.basename(self.source)

        deb_utils.extract_deb(deb_file, dst, logger.debug)

        if not keep:
            deb_file.unlink()
