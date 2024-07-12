# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

from typing import Literal

import pydantic
import pytest
from craft_parts.plugins import PluginProperties


class FooProperties(PluginProperties, frozen=True):
    plugin: Literal["foo"] = "foo"
    foo_parameters: list[str] | None = None


VALID_FOO_DICTS = [
    {},
    {"foo-parameters": []},
    {"plugin": "foo", "foo-parameters": ["bar"]},
    {"source": "https://example.com/foo.git", "plugin": "foo"},
    {"ignored-property": True},
    {"foo": "also-ignored"},
]


@pytest.mark.parametrize("data", VALID_FOO_DICTS)
def test_properties_unmarshal_valid(data):
    prop = FooProperties.unmarshal(data)
    assert isinstance(prop, PluginProperties)


@pytest.mark.parametrize("data", [{"foo-invalid": True}])
def test_properties_unmarshal_invalid(data):
    with pytest.raises(
        pydantic.ValidationError, match="Extra inputs are not permitted"
    ):
        FooProperties.unmarshal(data)


def test_properties_marshal():
    prop = FooProperties.unmarshal({"foo-parameters": ["foo", "bar"]})
    assert prop.marshal() == {"source": None, "foo-parameters": ["foo", "bar"]}


def test_properties_defaults():
    prop = FooProperties.unmarshal({})
    assert prop.get_pull_properties() == []
    assert prop.get_build_properties() == ["source", "foo-parameters"]
