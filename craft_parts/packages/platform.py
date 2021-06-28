# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Helpers to determine the repository for the platform."""

from craft_parts import errors
from craft_parts.utils import os_utils

_DEB_BASED_PLATFORM = ["ubuntu", "debian", "elementary OS", "elementary", "neon"]


def is_deb_based(distro=None) -> bool:
    """Verify the distribution packaging system.

    :param distro: The distribution name.

    :return: Whether the distribution uses .deb packages.
    """
    if not distro:
        try:
            distro = os_utils.OsRelease().id()
        except errors.OsReleaseIdError:
            distro = "unknown"
    return distro in _DEB_BASED_PLATFORM
