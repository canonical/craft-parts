# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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

"""The RPM source handler."""

import logging
import os
import subprocess
import tarfile
from pathlib import Path
from typing import List, Optional

from overrides import override

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler

logger = logging.getLogger(__name__)


class RpmSource(FileSourceHandler):
    """The "rpm" file source handler."""

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
        self._check_invalid_options("rpm", invalid_options)
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_checksum=source_checksum,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
        )

    @override
    def provision(
        self,
        dst: Path,
        keep: bool = False,
        src: Optional[Path] = None,
    ) -> None:
        """Extract rpm file contents to the part source dir."""
        rpm_path = src or self.part_src_dir / os.path.basename(self.source)
        command = ["rpm2archive", "-"]

        with rpm_path.open("rb") as rpm:
            try:
                with subprocess.Popen(
                    command, stdin=rpm, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ) as archive:
                    with tarfile.open(mode="r|*", fileobj=archive.stdout) as tar:
                        tar.extractall(path=dst)
            except (tarfile.TarError, subprocess.CalledProcessError) as err:
                raise errors.InvalidRpmPackage(rpm_path.name) from err

        if not keep:
            rpm_path.unlink()
