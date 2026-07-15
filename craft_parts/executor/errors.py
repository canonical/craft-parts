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

"""Executor error definitions."""

from craft_parts import errors


class EnvironmentChangedError(RuntimeError):
    """Environment between two lifecycle executions changed."""


class BuildSlicesMountError(errors.PartsError):
    """Failed to mount the build-slices merged root.

    :param mountpoint: The filesystem mount point.
    :param message: The error message.
    """

    def __init__(self, mountpoint: str, message: str) -> None:
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to mount build-slices merged root on {mountpoint}: {message}"
        resolution = "Ensure unionfs-fuse is installed and FUSE is available."

        super().__init__(brief=brief, resolution=resolution)


class BuildSlicesUnmountError(errors.PartsError):
    """Failed to unmount the build-slices merged root.

    :param mountpoint: The filesystem mount point.
    :param message: The error message.
    """

    def __init__(self, mountpoint: str, message: str) -> None:
        self.mountpoint = mountpoint
        self.message = message
        brief = f"Failed to unmount build-slices merged root {mountpoint}: {message}"

        super().__init__(brief=brief)
