# noqa: A005 (this module shadows the stdlib platform module)
# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2023 Canonical Ltd.
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

import distro

_DEB_BASED_PLATFORM = ["ubuntu", "debian", "elementary OS", "elementary", "neon"]
_YUM_BASED_PLATFORM = ["centos"]
_DNF_BASED_PLATFORM = ["almalinux"]


def _check(distro_name: str | None, platform_distros: list[str]) -> bool:
    """Check if `distro_name` is included in the specified platform distros.

    If the indicated distro is None it will be retrieved from the `distro`
    module or treated as "unknown" when unavailable.
    """
    if not distro_name:
        distro_name = distro.id() or "unknown"
    return distro_name in platform_distros


def is_deb_based(distro: str | None = None) -> bool:
    """Verify the distribution packaging system.

    :param distro: The distribution name.

    :return: Whether the distribution uses .deb packages.
    """
    return _check(distro, _DEB_BASED_PLATFORM)


def is_yum_based(distro: str | None = None) -> bool:
    """Verify the distribution packaging system.

    :param distro: The distribution name.

    :return: Whether the distribution handles packages through YUM.
    """
    return _check(distro, _YUM_BASED_PLATFORM)


def is_dnf_based(distro: str | None = None) -> bool:
    """Verify the distribution packaging system.

    :param distro: The distribution name.

    :return: Whether the distribution handles packages through DNF.
    """
    return _check(distro, _DNF_BASED_PLATFORM)
