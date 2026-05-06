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

"""Overlay error definitions."""

from craft_parts import errors


class OverlayError(errors.PartsError):
    """Base class for overlay handler errors."""


class OverlayMountError(OverlayError):
    """Failed to mount an overlay filesystem.

    :param mountpoint: The filesystem mount point.
    :param message: The error message.
    """

    def __init__(self, mountpoint: str, message: str) -> None:
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to mount overlay on {mountpoint}: {message}"

        super().__init__(brief=brief)


class OverlayUnmountError(OverlayError):
    """Failed to unmount an overlay filesystem.

    :param mountpoint: The filesystem mount point.
    :param message: The error message.
    """

    def __init__(self, mountpoint: str, message: str) -> None:
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to unmount {mountpoint}: {message}"

        super().__init__(brief=brief)


class OverlayChrootExecutionError(OverlayError):
    """Failed to execute in a chroot environment."""

    def __init__(self, message: str) -> None:
        self.message = message
        brief = f"Overlay environment execution error: {message}"

        super().__init__(brief=brief)


class IncompatibleChrootError(OverlayError):
    """Failed to use host package sources because chroot is incompatible.

    :param key: Distribution attribute which was tested.
    :param host: Value from the host distribution which was tested.
    :param chroot: Value from the chroot distribution which was tested.
    """

    def __init__(self, key: str, host: str, chroot: str) -> None:
        self.message = f"attribute {key} expected to be {host} found {chroot}"
        brief = f"Unable to use host sources: {self.message}"

        super().__init__(brief=brief)
