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
from typing import Union


class ProjectDirs:
    """The project's main work directories.

    :param work_dir: The parent directory containing the parts, prime and stage
        subdirectories. If not specified, the current directory will be used.

    :ivar work_dir: The root of the work directories used for project processing.
    :ivar parts_dir: The directory containing work subdirectories for each part.
    :ivar overlay_dir: The directory containing work subdirectories for overlays.
    :ivar overlay_mount_dir: The mountpoint for the overlay filesystem.
    :ivar overlay_packages_dir: The cache directory for overlay packages.
    :ivar overlay_work_dir: The work directory for the overlay filesystem.
    :ivar stage_dir: The staging area containing installed files from all parts.
    :ivar prime_dir: The primed tree containing the final artifacts to deploy.
    """

    def __init__(self, *, work_dir: Union[Path, str] = "."):
        self.project_dir = Path().expanduser().resolve()
        self.work_dir = Path(work_dir).expanduser().resolve()
        self.parts_dir = self.work_dir / "parts"
        self.overlay_dir = self.work_dir / "overlay"
        self.overlay_mount_dir = self.overlay_dir / "overlay"
        self.overlay_packages_dir = self.overlay_dir / "packages"
        self.overlay_work_dir = self.overlay_dir / "work"
        self.stage_dir = self.work_dir / "stage"
        self.prime_dir = self.work_dir / "prime"
