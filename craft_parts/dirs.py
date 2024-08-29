# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2024 Canonical Ltd.
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

from collections.abc import Sequence
from pathlib import Path
from types import MappingProxyType

from craft_parts.errors import PartitionNotFound, PartitionUsageError
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
        partitions: Sequence[str] | None = None,
        work_dir: Path | str = ".",
    ) -> None:
        partition_utils.validate_partition_names(partitions)
        self.project_dir = Path().expanduser().resolve()
        self.work_dir = Path(work_dir).expanduser().resolve()
        self.parts_dir = self.work_dir / "parts"
        self.overlay_dir = self.work_dir / "overlay"
        self.overlay_mount_dir = self.overlay_dir / "overlay"
        self.overlay_packages_dir = self.overlay_dir / "packages"
        self.overlay_work_dir = self.overlay_dir / "work"
        self.stage_dir = self.work_dir / "stage"
        self.prime_dir = self.work_dir / "prime"
        if partitions:
            self._partitions: Sequence[str] | None = partitions
            self.partition_dir: Path | None = self.work_dir / "partitions"
        else:
            self._partitions = None
            self.partition_dir = None

        self.stage_dirs = MappingProxyType(
            partition_utils.get_partition_dir_map(
                base_dir=self.work_dir, partitions=partitions, suffix="stage"
            )
        )
        self.prime_dirs = MappingProxyType(
            partition_utils.get_partition_dir_map(
                base_dir=self.work_dir, partitions=partitions, suffix="prime"
            )
        )

    def _validate_requested_partition(
        self, dir_name: str, partition: str | None = None
    ) -> None:
        """Ensure the requested partition is valid."""
        if self._partitions:
            if not partition:
                raise PartitionUsageError(
                    error_list=[
                        f"Partitions are enabled, you must specify which partition's {dir_name!r} you want."
                    ],
                    partitions=self._partitions,
                )
            if partition not in self._partitions:
                raise PartitionNotFound(partition, self._partitions)

    def get_stage_dir(self, partition: str | None = None) -> Path:
        """Get the stage directory for the given partition."""
        self._validate_requested_partition("stage_dir", partition)
        return self.stage_dirs[partition]

    def get_prime_dir(self, partition: str | None = None) -> Path:
        """Get the prime directory for the given partition."""
        self._validate_requested_partition("prime_dir", partition)
        return self.prime_dirs[partition]
