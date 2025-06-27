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
import pytest
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins import PluginProperties
from craft_parts.plugins.java_plugin import JavaPlugin
from overrides import override


class DummyJavaPlugin(JavaPlugin):
    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        return set()

    @override
    def get_build_commands(self) -> list[str]:
        return []


def test_java_plugin_no_java(part_info, mocker):
    properties = PluginProperties.unmarshal({"source": "."})
    plugin = DummyJavaPlugin(properties=properties, part_info=part_info)

    def _check_java(self, javac: str):
        return None, ""

    mocker.patch.object(JavaPlugin, "_check_java", _check_java)

    assert plugin.get_build_environment() == {}


def test_java_plugin_jre_not_17(part_info, mocker):
    orig_check_java = JavaPlugin._check_java

    def _check_java(self, javac: str):
        if "17" not in javac:
            return None, ""
        return orig_check_java(self, javac)

    mocker.patch.object(JavaPlugin, "_check_java", _check_java)

    properties = PluginProperties.unmarshal({"source": "."})
    plugin = DummyJavaPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert len(env) == 1
    assert "17" in env["JAVA_HOME"]


@pytest.mark.parametrize(
    ("part_properties", "expected_self_contained"),
    [({}, False), ({"build-attributes": ["self-contained"]}, True)],
)
def test_java_plugin_self_contained(part_properties, expected_self_contained, new_dir):
    cache_dir = new_dir / "cache"
    cache_dir.mkdir()
    part_info = PartInfo(
        project_info=ProjectInfo(
            application_name="testcraft",
            cache_dir=cache_dir,
        ),
        part=Part("my-part", part_properties),
    )

    properties = PluginProperties.unmarshal(part_properties)
    plugin = DummyJavaPlugin(properties=properties, part_info=part_info)

    assert plugin._is_self_contained() == expected_self_contained
