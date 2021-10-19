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

from craft_parts.packages import errors


def test_package_backend_not_supported():
    err = errors.PackageBackendNotSupported("apt")
    assert err.backend == "apt"
    assert err.brief == "Package backend 'apt' is not supported on this environment."
    assert err.details is None
    assert err.resolution is None


def test_package_not_found():
    err = errors.PackageNotFound("foobar")
    assert err.package_name == "foobar"
    assert err.brief == "Package not found: foobar."
    assert err.details is None
    assert err.resolution is None


def test_packages_not_found():
    err = errors.PackagesNotFound(["foo", "bar"])
    assert err.packages == ["foo", "bar"]
    assert err.brief == (
        "Failed to find installation candidate for packages: 'bar' and 'foo'."
    )
    assert err.details is None
    assert err.resolution == (
        "Make sure the repository configuration and package names are correct."
    )


def test_package_fetch_error():
    err = errors.PackageFetchError("something bad happened")
    assert err.message == "something bad happened"
    assert err.brief == "Failed to fetch package: something bad happened."
    assert err.details is None
    assert err.resolution is None


def test_package_list_refresh_error():
    err = errors.PackageListRefreshError("something bad happened")
    assert err.message == "something bad happened"
    assert err.brief == "Failed to refresh package list: something bad happened."
    assert err.details is None
    assert err.resolution is None


def test_package_broken():
    err = errors.PackageBroken("foobar", deps=["foo", "bar"])
    assert err.package_name == "foobar"
    assert err.deps == ["foo", "bar"]
    assert err.brief == "Package 'foobar' has unmet dependencies: foo, bar."
    assert err.details is None
    assert err.resolution is None


def test_file_provider_not_found():
    err = errors.FileProviderNotFound(file_path="/some/path")
    assert err.file_path == "/some/path"
    assert err.brief == "/some/path is not provided by any package."
    assert err.details is None
    assert err.resolution is None


def test_build_package_not_found():
    err = errors.BuildPackageNotFound("foobar")
    assert err.package == "foobar"
    assert err.brief == "Cannot find package listed in 'build-packages': foobar"
    assert err.details is None
    assert err.resolution is None


def test_build_packages_not_installed():
    err = errors.BuildPackagesNotInstalled(packages=["foo", "bar"])
    assert err.packages == ["foo", "bar"]
    assert err.brief == "Cannot install all requested build packages: foo, bar"
    assert err.details is None
    assert err.resolution is None


def test_packages_download_error():
    err = errors.PackagesDownloadError(packages=["foo", "bar"])
    assert err.packages == ["foo", "bar"]
    assert err.brief == "Failed to download all requested packages: foo, bar"
    assert err.details is None
    assert err.resolution == (
        "Make sure the network configuration and package names are correct."
    )


def test_unpack_error():
    err = errors.UnpackError("foobar")
    assert err.package == "foobar"
    assert err.brief == "Error unpacking 'foobar'"
    assert err.details is None
    assert err.resolution is None


def test_snap_unavailable():
    err = errors.SnapUnavailable(snap_name="word-salad", snap_channel="stable")
    assert err.snap_name == "word-salad"
    assert err.snap_channel == "stable"
    assert err.brief == "Failed to install or refresh snap 'word-salad'."
    assert err.details == (
        "'word-salad' does not exist or is not available on channel 'stable'."
    )
    assert err.resolution == (
        "Use `snap info word-salad` to get a list of channels the snap "
        "is available on."
    )


def test_snap_install_error():
    err = errors.SnapInstallError(snap_name="word-salad", snap_channel="stable")
    assert err.snap_name == "word-salad"
    assert err.snap_channel == "stable"
    assert err.brief == "Error installing snap 'word-salad' from channel 'stable'."
    assert err.details is None
    assert err.resolution is None


def test_snap_download_error():
    err = errors.SnapDownloadError(snap_name="word-salad", snap_channel="stable")
    assert err.snap_name == "word-salad"
    assert err.snap_channel == "stable"
    assert err.brief == "Error downloading snap 'word-salad' from channel 'stable'."
    assert err.details is None
    assert err.resolution is None


def test_snap_refresh_error():
    err = errors.SnapRefreshError(snap_name="word-salad", snap_channel="stable")
    assert err.snap_name == "word-salad"
    assert err.snap_channel == "stable"
    assert err.brief == "Error refreshing snap 'word-salad' to channel 'stable'."
    assert err.details is None
    assert err.resolution is None


def test_snap_get_assertion_error():
    err = errors.SnapGetAssertionError(
        assertion_params=["snap-revision=42", "snap-name=foo"]
    )
    assert err.assertion_params == ["snap-revision=42", "snap-name=foo"]
    assert err.brief == (
        "Error retrieving assertion with parameters ['snap-revision=42', "
        "'snap-name=foo']"
    )
    assert err.details is None
    assert err.resolution == "Verify the assertion exists and try again."


def test_snapd_connection_error():
    err = errors.SnapdConnectionError(
        snap_name="word-salad", url="http+unix://%2Frun%2Fsnapd.socket/v2/whatever"
    )
    assert err.snap_name == "word-salad"
    assert err.url == "http+unix://%2Frun%2Fsnapd.socket/v2/whatever"
    assert err.brief == (
        "Failed to get information for snap 'word-salad': could not connect "
        "to 'http+unix://%2Frun%2Fsnapd.socket/v2/whatever'."
    )
    assert err.details is None
    assert err.resolution is None
