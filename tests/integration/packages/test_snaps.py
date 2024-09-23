# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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
"""Integration tests for interacting with snapd."""

import pathlib
from collections.abc import Sequence

import pytest
import pytest_check  # type: ignore[import]
from craft_parts.packages import snaps


def test_get_installed_snaps_success():
    """Test that get_installed_snaps returns a list of snaps."""
    actual = snaps.get_installed_snaps()

    for snap in actual:
        name, _, revision = snap.partition("=")
        pytest_check.is_true(len(name) >= 1)
        if revision.startswith("x"):
            # Locally installed snaps should be of the form "x<int>"
            with pytest_check.check():
                int(revision[1:])
        else:
            # Store-instaled snaps should simply have an integer revision.
            with pytest_check.check():
                int(revision)


@pytest.mark.parametrize(
    "snaps_list",
    [
        {"snapcraft", "ruff"},
        {"snapcraft/7.x/stable"},
    ],
)
def test_download_snaps_success(new_path: pathlib.Path, snaps_list: Sequence[str]):

    snaps.download_snaps(snaps_list=snaps_list, directory=new_path)

    for snap in snaps_list:
        snap_name, _, snap_channel = snap.partition("/")
        assert len(list(new_path.glob(f"{snap_name}*.snap"))) == 1
        assert len(list(new_path.glob(f"{snap_name}*.assert"))) == 1
