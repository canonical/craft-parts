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
from typing import List, Optional, Union

from craft_parts.utils import os_utils

from . import errors

logger = logging.getLogger(__name__)


class OverlayFS:
    """Linux overlayfs operations."""

    def __init__(
        self, *, lower_dir: Union[Path, List[Path]], upper_dir: Path, work_dir: Path
    ):
        if not isinstance(lower_dir, list):
            lower_dir = [lower_dir]

        self._lower_dir = lower_dir
        self._upper_dir = upper_dir
        self._work_dir = work_dir
        self._mountpoint: Optional[Path] = None

    def mount(self, mountpoint: Path) -> None:
        """Mount an overlayfs."""
        logger.debug("mount overlayfs on %s", self._mountpoint)
        lower_dir = ":".join([str(p) for p in self._lower_dir])

        try:
            os_utils.mount(
                "overlay",
                str(mountpoint),
                "-toverlay",
                "-olowerdir={!s},upperdir={!s},workdir={!s}".format(
                    lower_dir, self._upper_dir, self._work_dir
                ),
            )
        except CalledProcessError as err:
            raise errors.OverlayMountError(str(mountpoint), message=str(err))

        self._mountpoint = mountpoint

    def unmount(self) -> None:
        """Umount an overlayfs."""
        if not self._mountpoint:
            return

        logger.debug("unmount overlayfs from %s", self._mountpoint)
        try:
            os_utils.umount(str(self._mountpoint))
        except CalledProcessError as err:
            raise errors.OverlayMountError(str(self._mountpoint), message=str(err))

        self._mountpoint = None


def is_whiteout_file(path: Path) -> bool:
    """Verify if the given path corresponds to a whiteout file.

    :param path: The path of the file to verify.

    :return: Whether the given path is an overlayfs whiteout.
    """
    if not path.is_char_device() or path.is_symlink():
        return False

    rdev = os.stat(path).st_rdev

    return os.major(rdev) == 0 and os.minor(rdev) == 0


def is_opaque_dir(path: Path) -> bool:
    """Verify if the given path corresponds to an opaque directory.

    :param path: The path of the file to verify.

    :return: Whether the given path is an overlayfs opaque directory.
    """
    if not path.is_dir() or path.is_symlink():
        return False

    try:
        value = os.getxattr(path, "trusted.overlay.opaque")
    except OSError:
        return False

    return value == b"y"
