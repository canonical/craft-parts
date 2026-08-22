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

import pytest
from craft_parts.utils import deb_utils


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("bash_bins", True, id="slice"),
        pytest.param("bash", False, id="package"),
        pytest.param("", False, id="empty-string"),
    ],
)
def test_is_chisel_slice(name, expected):
    assert deb_utils._is_chisel_slice(name) == expected


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        pytest.param(["bash_bins", "openssl_data"], True, id="all-slices"),
        pytest.param(["bash_bins", "curl"], True, id="mixed"),
        pytest.param(["curl", "libxml2"], False, id="all-debs"),
        pytest.param([], False, id="empty-list"),
    ],
)
def test_has_slices(names, expected):
    assert deb_utils.has_slices(names) == expected


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        pytest.param(["curl", "libxml2"], True, id="all-debs"),
        pytest.param(["bash_bins", "curl"], True, id="mixed"),
        pytest.param(["bash_bins", "openssl_data"], False, id="all-slices"),
        pytest.param([], False, id="empty-list"),
    ],
)
def test_has_debs(names, expected):
    assert deb_utils.has_debs(names) == expected
