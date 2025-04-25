# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022-2023 Canonical Ltd.
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


@pytest.fixture
def fake_apt_cache(mocker):
    def get_installed_version(
        package_name,
        resolve_virtual_packages=False,  # noqa: FBT002
    ):  # pylint: disable=unused-argument
        if "installed" in package_name:
            return "1.0"
        if "new-version" in package_name:
            return "3.0"
        if "resolved-virtual-package" in package_name:
            return "1.0"
        if package_name == "versioned-package":
            return "2.0"
        if package_name.endswith("package"):
            return "1.0"
        return None

    fake = mocker.patch("craft_parts.packages.deb.AptCache")
    fake.return_value.__enter__.return_value.get_installed_version.side_effect = (
        get_installed_version
    )
    return fake


@pytest.fixture
def fake_deb_run(mocker):
    return mocker.patch("craft_parts.packages.deb.process_run")


@pytest.fixture
def fake_yum_run(mocker):
    return mocker.patch("craft_parts.packages.yum.process_run")


@pytest.fixture
def fake_dnf_run(mocker):
    return mocker.patch("craft_parts.packages.dnf.process_run")
