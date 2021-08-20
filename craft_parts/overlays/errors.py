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

    def __init__(self, mountpoint: str, message: str):
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to mount overlay on {mountpoint}: {message}"

        super().__init__(brief=brief)


class OverlayUnmountError(OverlayError):
    """Failed to unmount an overlay filesystem.

    :param mountpoint: The filesystem mount point.
    :param message: The error message.
    """

    def __init__(self, mountpoint: str, message: str):
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to unmount {mountpoint}: {message}"

        super().__init__(brief=brief)
