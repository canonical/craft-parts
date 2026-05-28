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

from craft_parts.packages import deb


def test_get_installed_packages_returns_system_packages():
    """Verify installed Debian packages can be queried without python-apt."""
    packages = deb.Ubuntu.get_installed_packages()

    assert packages
    assert all("=" in package for package in packages)
    assert any(package.startswith("dpkg=") for package in packages)
