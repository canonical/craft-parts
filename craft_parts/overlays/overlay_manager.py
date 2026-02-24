# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeVar, cast

from typing_extensions import Self

from craft_parts import packages
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part

from . import chroot
from .overlay_fs import OverlayFS

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _defer_evaluation(method: Callable[..., _T]) -> Callable[..., _T]:
    """Wrap methods to defer evaluation.

    Defer evaluation of proxied class methods to happen at execution time.
    Used to pass repositories to chroot environments in a way that the
    repository type will only be evaluated inside the chroot environment.
    """
    method_name = getattr(method, "__name__", None)
    instance = getattr(method, "__self__", None)

    if instance is None or method_name is None:
        raise TypeError("Only bound methods can be deferred")

    def _thunk(*args: Any, **kwargs: Any) -> _T:
        method = cast(Callable[..., _T], getattr(instance, method_name))
        return method(*args, **kwargs)

    return _thunk


class OverlayManager:
    """Execution time overlay mounting and package installation.

    :param project_info: The project information.
    :param part_list: A list of all parts in the project.
    :param base_layer_dir: The directory containing the overlay base, or None
        if the project doesn't use overlay parameters.
    :param cache_level: The number of part layers to be mounted before the
        package cache.
    """

    def __init__(
        self,
        *,
        project_info: ProjectInfo,
        part_list: list[Part],
        base_layer_dir: Path | None,
        cache_level: int,
    ) -> None:
        self._project_info = project_info
        self._part_list = part_list
        self._layer_dirs = [p.part_layer_dir for p in part_list]
        self._overlay_fs: OverlayFS | None = None
        self._base_layer_dir = base_layer_dir
        self._cache_level = cache_level

    @property
    def base_layer_dir(self) -> Path | None:
        """Return the path to the base layer, if any."""
        return self._base_layer_dir

    @property
    def cache_level(self) -> int:
        """The cache layer index above the base layer."""
        return self._cache_level

    def mount_layer(self, part: Part, *, pkg_cache: bool = False) -> None:
        """Mount the overlay step layer stack up to the given part.

        :param part: The part corresponding to the topmost layer to mount.
        :param pkg cache: Whether the package cache layer is enabled.
        """
        if not self._base_layer_dir:
            raise RuntimeError("request to mount overlay without a base layer")

        # The top layer index.
        index = self._part_list.index(part)

        # Lower layers without the cache layer.
        lowers = [self._base_layer_dir]
        lowers.extend(self._layer_dirs[0:index])

        # Insert the cache layer at the appropriate level. If the layer is 0,
        # it will be placed immediately above the base layer.
        if pkg_cache and index >= self._cache_level:
            level = self._cache_level + 1
            lowers = [
                *lowers[0:level],
                self._project_info.overlay_packages_dir,
                *lowers[level : index + 1],
            ]

        # The top layer.
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

        lowers = [self._base_layer_dir]
        lowers.extend(self._layer_dirs[0 : self._cache_level])

        # Lower dirs are stacked from right to left.
        lowers.reverse()

        self._overlay_fs = OverlayFS(
            lower_dirs=lowers,
            upper_dir=self._project_info.overlay_packages_dir,
            work_dir=self._project_info.overlay_work_dir,
        )

        logger.debug("Mount cache layer %d", self._cache_level)

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

        logger.debug("Refreshing packages list in overlay")

        mount_dir = self._project_info.overlay_mount_dir
        # Ensure we always run refresh_packages_list by resetting the cache
        packages.Repository.refresh_packages_list.cache_clear()  # type: ignore[attr-defined]
        chroot.chroot(
            mount_dir, _defer_evaluation(packages.Repository.refresh_packages_list)
        )

    def download_packages(self, package_names: list[str]) -> None:
        """Download packages and populate the overlay package cache.

        :param package_names: The list of packages to download.
        """
        self.run(
            _defer_evaluation(packages.Repository.download_packages),
            package_names,
        )

    def install_packages(self, package_names: list[str]) -> None:
        """Install packages on the overlay area using chroot.

        :param package_names: The list of packages to install.
        """
        self.run(
            _defer_evaluation(packages.Repository.install_packages),
            package_names,
            refresh_package_cache=False,
        )

    def run(self, target: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        """Run the given callable inside the chroot environment."""
        if not self._overlay_fs:
            raise RuntimeError("overlay filesystem not mounted")

        return chroot.chroot(
            self._project_info.overlay_mount_dir, target, *args, **kwargs
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
        pkg_cache: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        self._overlay_manager = overlay_manager
        self._overlay_manager.mkdirs()
        self._top_part = top_part
        self._pkg_cache = pkg_cache
        self._pid = os.getpid()

    def __enter__(self) -> Self:
        logger.debug("---- Enter layer mount context ----")
        self._overlay_manager.mount_layer(
            self._top_part,
            pkg_cache=self._pkg_cache,
        )
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        # prevent pychroot process leak
        if os.getpid() != self._pid:
            sys.exit()
        self._overlay_manager.unmount()
        logger.debug("---- Exit layer mount context ----")
        return False

    def install_packages(self, package_names: list[str]) -> None:
        """Install the specified packages on the local system.

        :param package_names: The list of packages to install.
        """
        self._overlay_manager.install_packages(package_names)


class PackageCacheMount:
    """Mount and umount the overlay package cache.

    :param overlay_manager: The overlay manager.
    """

    def __init__(self, overlay_manager: OverlayManager) -> None:
        self._overlay_manager = overlay_manager
        self._overlay_manager.mkdirs()
        self._pid = os.getpid()

    def __enter__(self) -> Self:
        logger.debug("---- Enter package cache mount context ----")
        self._overlay_manager.mount_pkg_cache()
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        # prevent pychroot process leak
        if os.getpid() != self._pid:
            sys.exit()
        self._overlay_manager.unmount()
        logger.debug("---- Exit package cache mount context ----")
        return False

    def refresh_packages_list(self) -> None:
        """Update the list of available packages in the overlay system."""
        self._overlay_manager.refresh_packages_list()

    def download_packages(self, package_names: list[str]) -> None:
        """Download the specified packages to the local system.

        :param package_names: The list of packages to download.
        """
        self._overlay_manager.download_packages(package_names)


class ChrootMount(LayerMount):
    """Context manager that mounts an overlay for step processing and runs code inside a chroot environment."""

    def __call__(self, target: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        """Synthax sugar method to run within chroot."""
        return self._overlay_manager.run(target, *args, **kwargs)
