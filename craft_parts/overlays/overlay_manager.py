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
import os
import sys
from pathlib import Path
from typing import List, Optional

from craft_parts import packages
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part

from . import chroot
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
        self._overlay_fs: Optional[OverlayFS] = None
        self._base_layer_dir = base_layer_dir

    @property
    def base_layer_dir(self) -> Optional[Path]:
        """Return the path to the base layer, if any."""
        return self._base_layer_dir

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
            raise RuntimeError("filesystem is not mounted")

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

    def refresh_packages_list(self) -> None:
        """Update the list of available packages in the overlay system."""
        if not self._overlay_fs:
            raise RuntimeError("overlay filesystem not mounted")

        mount_dir = self._project_info.overlay_mount_dir
        # Ensure we always run refresh_packages_list by resetting the cache
        packages.Repository.refresh_packages_list.cache_clear()
        chroot.chroot(mount_dir, packages.Repository.refresh_packages_list)

    def download_packages(self, package_names: List[str]) -> None:
        """Download packages and populate the overlay package cache.

        :param package_names: The list of packages to download.
        """
        if not self._overlay_fs:
            raise RuntimeError("overlay filesystem not mounted")

        mount_dir = self._project_info.overlay_mount_dir
        chroot.chroot(mount_dir, packages.Repository.download_packages, package_names)

    def install_packages(self, package_names: List[str]) -> None:
        """Install packages on the overlay area using chroot.

        :param package_names: The list of packages to install.
        """
        if not self._overlay_fs:
            raise RuntimeError("overlay filesystem not mounted")

        mount_dir = self._project_info.overlay_mount_dir
        chroot.chroot(
            mount_dir,
            packages.Repository.install_packages,
            package_names,
            refresh_package_cache=False,
        )


class LayerMount:
    """Mount the overlay layer stack for step processing.

    :param overlay_manager: The overlay manager.
    :param top_part: The topmost part to mount.
    :param pkg_cache: Whether to mount the overlay package cache.
    """

    def __init__(
        self,
        overlay_manager: OverlayManager,
        top_part: Part,
        pkg_cache: bool = True,
    ):
        self._overlay_manager = overlay_manager
        self._overlay_manager.mkdirs()
        self._top_part = top_part
        self._pkg_cache = pkg_cache
        self._pid = os.getpid()

    def __enter__(self):
        self._overlay_manager.mount_layer(
            self._top_part,
            pkg_cache=self._pkg_cache,
        )
        return self

    def __exit__(self, *exc):
        # prevent pychroot process leak
        if os.getpid() != self._pid:
            sys.exit()
        self._overlay_manager.unmount()
        return False

    def install_packages(self, package_names: List[str]) -> None:
        """Install the specified packages on the local system.

        :param package_names: The list of packages to install.
        """
        self._overlay_manager.install_packages(package_names)


class PackageCacheMount:
    """Mount and umount the overlay package cache.

    :param overlay_manager: The overlay manager.
    """

    def __init__(self, overlay_manager: OverlayManager):
        self._overlay_manager = overlay_manager
        self._overlay_manager.mkdirs()
        self._pid = os.getpid()

    def __enter__(self):
        self._overlay_manager.mount_pkg_cache()
        return self

    def __exit__(self, *exc):
        # prevent pychroot process leak
        if os.getpid() != self._pid:
            sys.exit()
        self._overlay_manager.unmount()
        return False

    def refresh_packages_list(self) -> None:
        """Update the list of available packages in the overlay system."""
        self._overlay_manager.refresh_packages_list()

    def download_packages(self, package_names: List[str]) -> None:
        """Download the specified packages to the local system.

        :param package_names: The list of packages to download.
        """
        self._overlay_manager.download_packages(package_names)
