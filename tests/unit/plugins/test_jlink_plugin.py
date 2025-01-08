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


import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.jlink_plugin import JLinkPlugin


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_jlink_plugin_defaults(part_info):
    """Validate default settings of jlink plugin."""
    properties = JLinkPlugin.properties_class.unmarshal({"source": "."})
    plugin = JLinkPlugin(properties=properties, part_info=part_info)

    assert len(plugin.get_build_packages()) == 1
    assert "openjdk-21-jdk" in plugin.get_build_packages()

    assert plugin.get_build_environment() == {}


def test_jlink_plugin_java_version(part_info):
    """Validate setting of jlink version."""
    properties = JLinkPlugin.properties_class.unmarshal(
        {"source": ".", "jlink-java-version": "17"}
    )
    plugin = JLinkPlugin(properties=properties, part_info=part_info)

    assert len(plugin.get_build_packages()) == 1
    assert "openjdk-17-jdk" in plugin.get_build_packages()


def test_jlink_plugin_jar_files(part_info):
    """Validate setting of jlink version."""
    properties = JLinkPlugin.properties_class.unmarshal(
        {"source": ".", "jlink-jars": ["foo.jar"]}
    )
    plugin = JLinkPlugin(properties=properties, part_info=part_info)

    assert "PROCESS_JARS=${CRAFT_STAGE}/foo.jar" in plugin.get_build_commands()
