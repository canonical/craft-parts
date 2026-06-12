# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
"""Integration tests for Debian package queries."""

import subprocess
from pathlib import Path

import pytest
from craft_parts.packages import deb


@pytest.fixture
def purge_hello():
    """Ensure hello is not installed before the test and clean up after."""
    subprocess.run(
        ["apt-get", "purge", "-y", "--autoremove", "hello"],
        check=False,
        capture_output=True,
    )
    yield
    subprocess.run(
        ["apt-get", "purge", "-y", "--autoremove", "hello"],
        check=False,
        capture_output=True,
    )


def test_get_installed_packages_returns_system_packages():
    """Verify installed Debian packages can be queried without python-apt."""
    packages = deb.Ubuntu.get_installed_packages()

    assert packages
    assert all(
        len(parts) == 2 and all(parts)
        for package in packages
        for parts in [package.split("=", 1)]
    )
    assert any(package.startswith("dpkg=") for package in packages)


@pytest.mark.requires_root
def test_install_packages_installs_package_and_returns_version(purge_hello):
    """Verify install_packages installs a package and reports its version."""
    installed = deb.Ubuntu.install_packages(["hello"])

    assert any(package.startswith("hello=") for package in installed)
    assert Path("/usr/bin/hello").is_file()


@pytest.mark.requires_root
def test_install_packages_already_installed_returns_version(purge_hello):
    """Verify install_packages is idempotent and still returns a version."""
    deb.Ubuntu.install_packages(["hello"])
    deb.Ubuntu.refresh_packages_list.cache_clear()

    installed = deb.Ubuntu.install_packages(["hello"])

    assert any(package.startswith("hello=") for package in installed)
