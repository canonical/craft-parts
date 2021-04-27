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
