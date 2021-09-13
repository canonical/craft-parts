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

"""Overlay mount operations and package installation helpers."""

import logging
from pathlib import Path
from typing import List, Optional

from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part

from .overlay_fs import OverlayFS

logger = logging.getLogger(__name__)


class OverlayManager:
    """Execution time overlay mounting and package installation.

    :param project_info: The project information.
    :param part_list: A list of all parts in the project.
    :param base_layer_dir: The directory containing the overlay base, or None
        if the project doesn't use overlay parameters.
    """

    def __init__(
        self,
        *,
        project_info: ProjectInfo,
        part_list: List[Part],
        base_layer_dir: Optional[Path]
    ):
        self._project_info = project_info
        self._part_list = part_list
        self._layer_dirs = [p.part_layer_dir for p in part_list]
        self._overlay_mount_dir = project_info.overlay_mount_dir
        self._overlay_fs: Optional[OverlayFS] = None
        self._base_layer_dir = base_layer_dir

    def mount_layer(self, part: Part, *, pkg_cache: bool = False) -> None:
        """Mount the overlay step layer stack up to the given part.

        :param part: The part corresponding to the topmost layer to mount.
        :param pkg cache: Whether the package cache layer is enabled.
        """
        if not self._base_layer_dir:
            raise RuntimeError("request to mount overlay without a base layer")

        lowers = [self._base_layer_dir]

        if pkg_cache:
            lowers.append(self._project_info.overlay_packages_dir)

        index = self._part_list.index(part)
        lowers.extend(self._layer_dirs[0:index])
        upper = self._layer_dirs[index]

        # lower dirs are stacked from right to left
        lowers.reverse()

        self._overlay_fs = OverlayFS(
            lower_dirs=lowers,
            upper_dir=upper,
            work_dir=self._project_info.overlay_work_dir,
        )

        self._overlay_fs.mount(self._project_info.overlay_mount_dir)

    def mount_pkg_cache(self) -> None:
        """Mount the overlay step package cache layer."""
        if not self._base_layer_dir:
            raise RuntimeError(
                "request to mount the overlay package cache without a base layer"
            )

        self._overlay_fs = OverlayFS(
            lower_dirs=[self._base_layer_dir],
            upper_dir=self._project_info.overlay_packages_dir,
            work_dir=self._project_info.overlay_work_dir,
        )

        self._overlay_fs.mount(self._project_info.overlay_mount_dir)

    def unmount(self) -> None:
        """Unmount the overlay step layer stack."""
        if not self._overlay_fs:
            logger.warning("overlay filesystem not mounted")
            return

        self._overlay_fs.unmount()
        self._overlay_fs = None

    def mkdirs(self) -> None:
        """Create overlay directories and mountpoints."""
        for overlay_dir in [
            self._project_info.overlay_mount_dir,
            self._project_info.overlay_packages_dir,
            self._project_info.overlay_work_dir,
        ]:
            overlay_dir.mkdir(parents=True, exist_ok=True)
