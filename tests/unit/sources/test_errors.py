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

from craft_parts.sources import errors


def test_invalid_source_type():
    err = errors.InvalidSourceType("t-death.adf")
    assert err.source == "t-death.adf"
    assert err.brief == (
        "Failed to pull source: unable to determine source type of 't-death.adf'."
    )
    assert err.details is None
    assert err.resolution is None


def test_invalid_source_option():
    err = errors.InvalidSourceOption(source_type="lzx", option="source-depth")
    assert err.source_type == "lzx"
    assert err.option == "source-depth"
    assert err.brief == (
        "Failed to pull source: 'source-depth' cannot be used with a lzx source."
    )
    assert err.details is None
    assert err.resolution == "Make sure sources are correctly specified."


def test_incompatible_source_options():
    err = errors.IncompatibleSourceOptions(
        source_type="dms", options=["source-tag", "source-branch"]
    )
    assert err.source_type == "dms"
    assert err.options == ["source-tag", "source-branch"]
    assert err.brief == (
        "Failed to pull source: cannot specify both 'source-branch' and 'source-tag' "
        "for a dms source."
    )
    assert err.details is None
    assert err.resolution == "Make sure sources are correctly specified."


def test_checksum_mismatch():
    err = errors.ChecksumMismatch(expected="1234", obtained="5678")
    assert err.expected == "1234"
    assert err.obtained == "5678"
    assert err.brief == "Expected digest 1234, obtained 5678."
    assert err.details is None
    assert err.resolution is None


def test_source_update_unsupported():
    err = errors.SourceUpdateUnsupported("Xyz")
    assert err.name == "Xyz"
    assert err.brief == "Failed to update source: 'Xyz' sources don't support updating."
    assert err.details is None
    assert err.resolution is None


def test_network_request_error():
    err = errors.NetworkRequestError("it failed")
    assert err.message == "it failed"
    assert err.brief == "Network request error: it failed."
    assert err.details is None
    assert err.resolution == "Check the network and try again."


def test_source_not_found():
    err = errors.SourceNotFound("some_source")
    assert err.source == "some_source"
    assert err.brief == "Failed to pull source: 'some_source' not found."
    assert err.details is None
    assert err.resolution == "Make sure the source path is correct and accessible."


def test_invalid_snap_package():
    err = errors.InvalidSnapPackage("figlet.snap")
    assert err.snap_file == "figlet.snap"
    assert err.brief == "Snap 'figlet.snap' does not contain valid data."
    assert err.details is None
    assert err.resolution == "Ensure the source lists a proper snap file."


def test_pull_error():
    err = errors.PullError(command=["ls", "-l"], exit_code=66)
    assert err.command == ["ls", "-l"]
    assert err.exit_code == 66
    assert (
        err.brief == "Failed to pull source: command ['ls', '-l'] exited with code 66."
    )
    assert err.details is None
    assert err.resolution == "Make sure sources are correctly specified."


def test_vcs_error():
    err = errors.VCSError("cvs: everything failed")
    assert err.message == "cvs: everything failed"
    assert err.brief == "cvs: everything failed"
    assert err.details is None
    assert err.resolution is None
