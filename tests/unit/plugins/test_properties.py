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

from typing import Any, Dict, List, Optional

from craft_parts.plugins import PluginProperties


def test_properties_unmarshal():
    prop = PluginProperties.unmarshal({})
    assert isinstance(prop, PluginProperties)


class FooProperties(PluginProperties):
    foo_parameters: Optional[List[str]]

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "FooProperties":
        return cls(**data)


def test_properties_marshal():
    prop = FooProperties.unmarshal({"foo-parameters": ["foo", "bar"]})
    assert prop.marshal() == {"foo-parameters": ["foo", "bar"]}


def test_properties_defaults():
    prop = FooProperties.unmarshal({})
    assert prop.get_pull_properties() == []
    assert prop.get_build_properties() == ["foo-parameters"]
