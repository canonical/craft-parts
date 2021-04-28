# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

from craft_parts.packages import errors


def test_package_list_refresh_error():
    err = errors.PackageListRefreshError("something bad happened")
    assert err.message == "something bad happened"
    assert err.brief == ("Failed to refresh package list: something bad happened.")
    assert err.details is None
    assert err.resolution is None


def test_package_fetch_error():
    err = errors.PackageFetchError("something bad happened")
    assert err.message == "something bad happened"
    assert err.brief == ("Failed to fetch package: something bad happened.")
    assert err.details is None
    assert err.resolution is None


def test_package_not_found():
    err = errors.PackageNotFound("foobar")
    assert err.package_name == "foobar"
    assert err.brief == ("Package not found: foobar.")
    assert err.details is None
    assert err.resolution is None


def test_package_broken():
    err = errors.PackageBroken("foobar", deps=["foo", "bar"])
    assert err.package_name == "foobar"
    assert err.deps == ["foo", "bar"]
    assert err.brief == ("Package 'foobar' has unmet dependencies: foo, bar.")
    assert err.details is None
    assert err.resolution is None
