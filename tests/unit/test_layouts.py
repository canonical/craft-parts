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
from craft_parts.layouts import Layout, LayoutItem


def test_layout_item_marshal_unmarshal():
    data = {
        "mount": "/",
        "device": "(default)",
    }

    data_copy = deepcopy(data)

    spec = LayoutItem.unmarshal(data)
    assert spec.marshal() == data_copy


def test_layout_item_unmarshal_not_dict():
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
def test_layout_item_unmarshal_empty_entries(data, error_regex):
    with pytest.raises(
        pydantic.ValidationError,
        match=error_regex,
    ):
        LayoutItem.unmarshal(data)


def test_layout_marshal_unmarshal():
    data = [
        {
            "mount": "/",
            "device": "foo",
        },
        {
            "mount": "/bar",
            "device": "baz",
        },
    ]

    data_copy = deepcopy(data)
    spec = Layout.unmarshal(data)

    assert spec.marshal() == data_copy


def test_layout_unmarshal_not_list():
    with pytest.raises(TypeError) as raised:
        Layout.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
    assert str(raised.value) == "layout data is not a list"


@pytest.mark.parametrize(
    ("data", "error_regex"),
    [
        (
            [],
            r"1 validation error for Layout\n\s+Value should have at least 1 item after validation, not 0",
        ),
        (
            [
                {
                    "mount": "/",
                    "device": "foo",
                },
                {
                    "mount": "/",
                    "device": "foo",
                },
            ],
            r"1 validation error for Layout\n\s+Value error, Duplicate values in list",
        ),
        (
            [
                {
                    "mount": "/foo",
                    "device": "foo",
                },
            ],
            r"1 validation error for Layout\n\s+Value error, A filesystem first entry must map the '/' mount",
        ),
    ],
)
def test_layout_unmarshal_invalid(data, error_regex):
    with pytest.raises(
        pydantic.ValidationError,
        match=error_regex,
    ):
        Layout.unmarshal(data)
