# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

from copy import deepcopy

import pydantic
import pytest
from craft_parts.layouts import LayoutItem


def test_layout_item_marshal_unmarshal():
    data = {
        "mount": "/",
        "device": "(default)",
    }

    data_copy = deepcopy(data)

    spec = LayoutItem.unmarshal(data)
    assert spec.marshal() == data_copy


def test_unmarshal_not_dict():
    with pytest.raises(TypeError) as raised:
        LayoutItem.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
    assert str(raised.value) == "layout item data is not a dictionary"


@pytest.mark.parametrize(
    ("data", "error_regex"),
    [
        (
            {
                "mount": "",
                "device": "(default)",
            },
            r"1 validation error for LayoutItem\nmount\n\s+String should have at least 1 character",
        ),
        (
            {
                "mount": "/",
                "device": "",
            },
            r"1 validation error for LayoutItem\ndevice\n\s+String should have at least 1 character",
        ),
    ],
)
def test_unmarshal_empty_entries(data, error_regex):
    with pytest.raises(
        pydantic.ValidationError,
        match=error_regex,
    ):
        LayoutItem.unmarshal(data)
