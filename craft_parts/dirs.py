# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Definitions for project directories."""

from pathlib import Path
from types import MappingProxyType
from typing import Dict, Optional, Sequence, Union

from craft_parts.utils import partition_utils


class ProjectDirs:
    """The project's main work directories.

    :param work_dir: The parent directory containing the parts, prime and stage
        subdirectories. If not specified, the current directory will be used.
    :param partitions: If partitions are enabled, the list of partitions.

    :ivar work_dir: The root of the work directories used for project processing.
    :ivar parts_dir: The directory containing work subdirectories for each part.
    :ivar overlay_dir: The directory containing work subdirectories for overlays.
    :ivar overlay_mount_dir: The mountpoint for the overlay filesystem.
    :ivar overlay_packages_dir: The cache directory for overlay packages.
    :ivar overlay_work_dir: The work directory for the overlay filesystem.
    :ivar stage_dir: The staging area containing installed files from all parts.
    :ivar prime_dir: The primed tree containing the final artifacts to deploy.
    """

    def __init__(
        self,
        *,
        partitions: Optional[Sequence[str]] = None,
        work_dir: Union[Path, str] = ".",
    ):
        partition_utils.validate_partition_names(partitions)
        self.project_dir = Path().expanduser().resolve()
        self.work_dir = Path(work_dir).expanduser().resolve()
        self.parts_dir = self.work_dir / "parts"
        self.overlay_dir = self.work_dir / "overlay"
        self.overlay_mount_dir = self.overlay_dir / "overlay"
        self.overlay_packages_dir = self.overlay_dir / "packages"
        self.overlay_work_dir = self.overlay_dir / "work"
        self.base_stage_dir = self.work_dir / "stage"
        self.base_prime_dir = self.work_dir / "prime"
        if partitions:
            self._partitions: Sequence[Optional[str]] = partitions
            self.stage_dir = self.base_stage_dir / "default"
            self.prime_dir = self.base_prime_dir / "default"
            stage_dirs: Dict[Optional[str], Path] = {
                part: self.base_stage_dir / part for part in partitions
            }
            prime_dirs: Dict[Optional[str], Path] = {
                part: self.base_prime_dir / part for part in partitions
            }
        else:
            self._partitions = [None]
            self.stage_dir = self.base_stage_dir
            self.prime_dir = self.base_prime_dir
            stage_dirs = {None: self.stage_dir}
            prime_dirs = {None: self.prime_dir}
        self.stage_dirs = MappingProxyType(stage_dirs)
        self.prime_dirs = MappingProxyType(prime_dirs)

    def get_stage_dir(self, partition: Optional[str] = None) -> Path:
        """Get the stage directory for the given partition."""
        if partition not in self._partitions:
            raise ValueError(f"Unknown partition {partition}")
        return self.stage_dirs[partition]

    def get_prime_dir(self, partition: Optional[str] = None) -> Path:
        """Get the stage directory for the given partition."""
        if partition not in self._partitions:
            raise ValueError(f"Unknown partition {partition}")
        return self.prime_dirs[partition]
