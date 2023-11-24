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

import pytest
from craft_parts import errors, packages
from craft_parts.packages import platform
from craft_parts.packages.base import DummyRepository
from craft_parts.packages.deb import Ubuntu
from craft_parts.packages.dnf import DNFRepository
from craft_parts.packages.yum import YUMRepository

_deb_distros = {"ubuntu", "debian", "elementary OS", "elementary", "neon"}
_yum_distros = {"centos"}
_dnf_distros = {"almalinux"}
_all_distros = [
    "almalinux",
    "fedora",
    "centos",
    "debian",
    "ubuntu",
    "elementary OS",
    "elementary",
    "neon",
    "opensuse",
]


def test_deb_based_platforms():
    assert set(platform._DEB_BASED_PLATFORM) == _deb_distros


def test_is_deb_based():
    for distro in [*_all_distros, "other"]:
        assert platform.is_deb_based(distro) == (distro in _deb_distros)


def test_is_deb_based_default(mocker):
    for distro in _all_distros:
        mocker.patch("craft_parts.utils.os_utils.OsRelease.id", return_value=distro)
        assert platform.is_deb_based() == (distro in _deb_distros)


def test_is_deb_based_error(mocker):
    mocker.patch(
        "craft_parts.utils.os_utils.OsRelease.id", side_effect=errors.OsReleaseIdError()
    )
    assert platform.is_deb_based() is False


def test_yum_based_platforms():
    assert set(platform._YUM_BASED_PLATFORM) == _yum_distros


def test_is_yum_based():
    for distro in [*_all_distros, "other"]:
        assert platform.is_yum_based(distro) == (distro in _yum_distros)


def test_is_yum_based_default(mocker):
    for distro in _all_distros:
        mocker.patch("craft_parts.utils.os_utils.OsRelease.id", return_value=distro)
        assert platform.is_yum_based() == (distro in _yum_distros)


def test_is_yum_based_error(mocker):
    mocker.patch(
        "craft_parts.utils.os_utils.OsRelease.id", side_effect=errors.OsReleaseIdError()
    )
    assert platform.is_yum_based() is False


def test_dnf_based_platforms():
    assert set(platform._DNF_BASED_PLATFORM) == _dnf_distros


def test_is_dnf_based():
    for distro in [*_all_distros, "other"]:
        assert platform.is_dnf_based(distro) == (distro in _dnf_distros)


def test_is_dnf_based_default(mocker):
    for distro in _all_distros:
        mocker.patch("craft_parts.utils.os_utils.OsRelease.id", return_value=distro)
        assert platform.is_dnf_based() == (distro in _dnf_distros)


def test_is_dnf_based_error(mocker):
    mocker.patch(
        "craft_parts.utils.os_utils.OsRelease.id", side_effect=errors.OsReleaseIdError()
    )
    assert platform.is_dnf_based() is False


@pytest.mark.parametrize(
    ("distro", "repo"),
    [
        ("ubuntu", Ubuntu),
        ("almalinux", DNFRepository),
        ("centos", YUMRepository),
        ("other", DummyRepository),
    ],
)
def test_get_repository_for_platform(mocker, distro, repo):
    mocker.patch("craft_parts.utils.os_utils.OsRelease.id", return_value=distro)
    assert packages._get_repository_for_platform() == repo
