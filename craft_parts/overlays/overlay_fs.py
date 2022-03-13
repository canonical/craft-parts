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

"""Low level interface to OS overlayfs."""

import logging
import os
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, Optional

from craft_parts.utils import os_utils

from . import errors

logger = logging.getLogger(__name__)


class OverlayFS:
    """Linux overlayfs operations."""

    def __init__(self, *, lower_dirs: List[Path], upper_dir: Path, work_dir: Path):
        self._lower_dirs = lower_dirs
        self._upper_dir = upper_dir
        self._work_dir = work_dir
        self._mountpoint: Optional[Path] = None

    def mount(self, mountpoint: Path) -> None:
        """Mount an overlayfs.

        :param mountpoint: The filesystem mount point.

        :raises OverlayMountError: on mount error.
        """
        logger.debug("mount overlayfs on %s", mountpoint)
        lower_dir = ":".join([str(p) for p in self._lower_dirs])

        try:
            os_utils.mount_overlayfs(
                str(mountpoint),
                f"-olowerdir={lower_dir!s},upperdir={self._upper_dir!s},"
                f"workdir={self._work_dir!s}",
            )
        except CalledProcessError as err:
            raise errors.OverlayMountError(str(mountpoint), message=str(err)) from err

        self._mountpoint = mountpoint

    def unmount(self) -> None:
        """Umount an overlayfs.

        :raises OverlayUnmountError: on unmount error.
        """
        if not self._mountpoint:
            return

        logger.debug("unmount overlayfs from %s", self._mountpoint)
        try:
            os_utils.umount(str(self._mountpoint))
        except CalledProcessError as err:
            raise errors.OverlayUnmountError(
                str(self._mountpoint), message=str(err)
            ) from err

        self._mountpoint = None


def is_whiteout_file(path: Path) -> bool:
    """Verify if the given path corresponds to a whiteout file.

    Overlayfs whiteout files are represented as character devices
    with major and minor numbers set to 0.

    :param path: The path of the file to verify.

    :returns: Whether the given path is an overlayfs whiteout.
    """
    if not path.is_char_device() or path.is_symlink():
        return False

    rdev = os.stat(path).st_rdev

    return os.major(rdev) == 0 and os.minor(rdev) == 0


def is_opaque_dir(path: Path) -> bool:
    """Verify if the given path corresponds to an opaque directory.

    Overlayfs opaque directories are represented by directories with the
    extended attribute `trusted.overlay.opaque` set to `y`.

    :param path: The path of the file to verify.

    :returns: Whether the given path is an overlayfs opaque directory.
    """
    if not path.is_dir() or path.is_symlink():
        return False

    try:
        value = os.getxattr(path, "trusted.overlay.opaque")
    except OSError:
        return False

    return value == b"y"
