# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""Merged-root manager for the build-slices feature.

Present a union of the Chisel slices directory and the system root as a merged
root, then chroot into it to run a part's build step. Slice contents shadow the
base system and land on the default toolchain paths, and their absolute symlinks
resolve against the merged root instead of the real host system.
"""

import logging
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Literal, TypeVar

from typing_extensions import Self

from craft_parts.infos import ProjectInfo
from craft_parts.overlays import chroot
from craft_parts.parts import Part
from craft_parts.utils import os_utils

from . import errors

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class UnionFsFuse:
    """Low-level interface to unionfs-fuse.

    Union the slices directory over the system root with copy-on-write, so writes
    land in a throwaway branch and the real system tree is never modified.

    :param slices_dir: The directory holding the cut Chisel slices.
    :param cow_dir: The writable copy-on-write branch.
    :param lower_dir: The read-only base root (the system root by default).
    """

    def __init__(
        self, *, slices_dir: Path, cow_dir: Path, lower_dir: Path = Path("/")
    ) -> None:
        self._slices_dir = slices_dir
        self._cow_dir = cow_dir
        self._lower_dir = lower_dir
        self._mountpoint: Path | None = None

    def mount(self, mountpoint: Path) -> None:
        """Mount the union filesystem.

        Branches are listed highest-priority first: the copy-on-write branch
        receives all writes, the slices shadow the base, and the base root is
        read-only.

        :param mountpoint: The filesystem mount point.

        :raises BuildSlicesMountError: on mount error.
        """
        logger.debug("mount unionfs-fuse on %s", mountpoint)
        branches = f"{self._cow_dir}=RW:{self._slices_dir}=RO:{self._lower_dir}=RO"

        try:
            os_utils.mount_unionfs(mountpoint, "-o", "cow", branches)
        except CalledProcessError as err:
            raise errors.BuildSlicesMountError(
                str(mountpoint), message=str(err)
            ) from err

        self._mountpoint = mountpoint

    def unmount(self) -> None:
        """Unmount the union filesystem.

        :raises BuildSlicesUnmountError: on unmount error.
        """
        if not self._mountpoint:
            return

        logger.debug("unmount unionfs-fuse from %s", self._mountpoint.as_posix())
        try:
            os_utils.umount_fuse(self._mountpoint)
        except CalledProcessError as err:
            raise errors.BuildSlicesUnmountError(
                self._mountpoint.as_posix(), message=str(err)
            ) from err

        self._mountpoint = None


class BuildSlicesMount:
    """Mount the build-slices merged root and run a part's build inside a chroot.

    On enter, mount the union of the slices directory and the system root, then
    bind-mount the part's working directories into the merged root so the build
    can read and write them at their usual absolute paths. On exit, undo the bind
    mounts, unmount the union, and discard the copy-on-write branch.

    :param project_info: The project information.
    :param part: The part whose build step will run in the merged root.
    """

    def __init__(self, *, project_info: ProjectInfo, part: Part) -> None:
        self._project_info = project_info
        self._part = part
        self._dirs = project_info.dirs
        self._mountpoint = self._dirs.build_slices_mount_dir
        self._unionfs = UnionFsFuse(
            slices_dir=self._dirs.build_slices_dir,
            cow_dir=self._dirs.build_slices_cow_dir,
        )
        self._bind_mounts: list[Path] = []
        self._pid = os.getpid()

    def __enter__(self) -> Self:
        logger.debug("---- Enter build-slices mount context ----")
        self._mkdirs()
        self._unionfs.mount(self._mountpoint)
        self._bind_part_dirs()
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        # Prevent a chroot child process from tearing down the mounts.
        if os.getpid() != self._pid:
            sys.exit()
        self._unbind_part_dirs()
        self._unionfs.unmount()
        self._discard_cow()
        logger.debug("---- Exit build-slices mount context ----")
        return False

    def run(self, target: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        """Run the given callable inside the merged-root chroot."""
        return chroot.chroot(self._mountpoint, target, *args, **kwargs)

    def __call__(self, target: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        """Syntactic sugar to run within the chroot."""
        return self.run(target, *args, **kwargs)

    def _mkdirs(self) -> None:
        self._mountpoint.mkdir(parents=True, exist_ok=True)
        self._dirs.build_slices_cow_dir.mkdir(parents=True, exist_ok=True)

    def _part_working_dirs(self) -> list[Path]:
        """Return the host directories the build must access inside the chroot."""
        dirs = [
            self._part.part_src_dir,
            self._part.part_build_dir,
            *self._part.part_install_dirs.values(),
            *self._dirs.stage_dirs.values(),
            self._dirs.backstage_dir,
        ]
        # De-duplicate while preserving order.
        seen: set[Path] = set()
        unique: list[Path] = []
        for directory in dirs:
            if directory not in seen:
                seen.add(directory)
                unique.append(directory)
        return unique

    def _abs_in_merged(self, host_path: Path) -> Path:
        """Map a host absolute path to the same path inside the merged root."""
        return self._mountpoint / str(host_path).lstrip("/")

    def _bind_part_dirs(self) -> None:
        for src in self._part_working_dirs():
            if not src.exists():
                continue
            dst = self._abs_in_merged(src)
            dst.mkdir(parents=True, exist_ok=True)
            os_utils.mount(src, dst, "--bind")
            self._bind_mounts.append(dst)

    def _unbind_part_dirs(self) -> None:
        for dst in reversed(self._bind_mounts):
            self._safe_umount(dst)
        self._bind_mounts.clear()

    @staticmethod
    def _safe_umount(dst: Path) -> None:
        try:
            os_utils.umount(dst, "--lazy")
        except CalledProcessError:
            logger.warning("failed to unmount build-slices bind %s", dst)

    def _discard_cow(self) -> None:
        cow_dir = self._dirs.build_slices_cow_dir
        for child in cow_dir.glob("*"):
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
