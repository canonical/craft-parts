# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Exceptions raised by the packages handling subsystem."""

from typing import Sequence

from craft_parts.errors import PartsError


class PackagesError(PartsError):
    """Base class for package handler errors."""


class SnapUnavailable(PackagesError):
    """Failed to install or refresh a snap."""

    def __init__(self, *, snap_name: str, snap_channel: str):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Failed to install or refresh snap {snap_name!r}."
        details = (
            f"{snap_name!r} does not exist or is not available on channel "
            f"{snap_channel!r}."
        )
        resolution = (
            f"Use `snap info {snap_name}` to get a list of channels the snap "
            "is available on."
        )

        super().__init__(brief=brief, details=details, resolution=resolution)


class SnapInstallError(PackagesError):
    """Failed to install a snap."""

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error installing snap {snap_name!r} from channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapDownloadError(PackagesError):
    """Failed to download a snap."""

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error downloading snap {snap_name!r} from channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapRefreshError(PackagesError):
    """Failed to refresh a snap."""

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error refreshing snap {snap_name!r} to channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapGetAssertionError(PackagesError):
    """Failed to retrieve snap assertion."""

    def __init__(self, *, assertion_params: Sequence[str]) -> None:
        self.assertion_params = assertion_params
        brief = f"Error retrieving assertion with parameters {assertion_params!r}"
        resolution = "Verify the assertion exists and try again."

        super().__init__(brief=brief, resolution=resolution)


class SnapdConnectionError(PackagesError):
    """Failed to connect to snapd."""

    def __init__(self, *, snap_name: str, url: str) -> None:
        self.snap_name = snap_name
        self.url = url
        brief = (
            f"Failed to get information for snap {snap_name!r}: could not connect "
            f"to {url!r}."
        )

        super().__init__(brief=brief)
