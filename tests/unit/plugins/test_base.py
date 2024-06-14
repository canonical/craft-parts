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

from typing import Any, cast

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin, PluginProperties
from craft_parts.plugins.base import extract_plugin_properties


class FooPluginProperties(PluginProperties):
    """Test plugin properties."""

    name: str

    @classmethod
    def unmarshal(cls, data: dict[str, Any]):
        return cls(name=data.get("foo-name", "nothing"))


class FooPlugin(Plugin):
    """A test plugin."""

    properties_class = FooPluginProperties

    def get_build_snaps(self) -> set[str]:
        return {"build_snap"}

    def get_build_packages(self) -> set[str]:
        return {"build_package"}

    def get_build_environment(self) -> dict[str, str]:
        return {"ENV": "value"}

    def get_build_commands(self) -> list[str]:
        options = cast(FooPluginProperties, self._options)
        return ["hello", options.name]


def test_plugin(new_dir):
    part = Part("p1", {})
    project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=project_info, part=part)

    props = FooPluginProperties.unmarshal({"foo-name": "world"})
    plugin = FooPlugin(properties=props, part_info=part_info)

    validator = FooPlugin.validator_class(part_name=part.name, env="", properties=props)
    validator.validate_environment()

    assert plugin.get_build_snaps() == {"build_snap"}
    assert plugin.get_build_packages() == {"build_package"}
    assert plugin.get_build_environment() == {"ENV": "value"}
    assert plugin.get_out_of_source_build() is False
    assert plugin.get_build_commands() == ["hello", "world"]


def test_abstract_methods(new_dir):
    class FaultyPlugin(Plugin):
        """A plugin that doesn't implement abstract methods."""

    part = Part("p1", {})
    project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=project_info, part=part)

    expected = (
        r"^Can't instantiate abstract class FaultyPlugin with(out an implementation "
        r"for)? abstract methods '?get_build_commands'?, '?get_build_environment'?, "
        r"'?get_build_packages'?, '?get_build_snaps'?$"
    )

    with pytest.raises(TypeError, match=expected):
        FaultyPlugin(properties=None, part_info=part_info)  # type: ignore[reportGeneralTypeIssues]


def test_extract_plugin_properties():
    data = {
        "foo": True,
        "test": "yes",
        "test-one": 1,
        "test-two": 2,
        "not-test-three": 3,
    }

    plugin_data = extract_plugin_properties(data, plugin_name="test")
    assert plugin_data == {"test-one": 1, "test-two": 2}
