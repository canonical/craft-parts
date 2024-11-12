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
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.java_plugin import JavaPlugin
from craft_parts.plugins.maven_plugin import MavenPlugin


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_java_plugin_no_java(part_info, mocker):

    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    def _check_java(self, javac: str):
        return None, ""

    mocker.patch.object(JavaPlugin, "_check_java", _check_java)

    assert plugin.get_build_environment() == {}


def test_java_plugin_jre_21(part_info, mocker):

    orig_check_java = JavaPlugin._check_java

    def _check_java(self, javac: str):
        if "21" in javac:
            return None, ""
        return orig_check_java(self, javac)

    mocker.patch.object(JavaPlugin, "_check_java", _check_java)

    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert len(env) == 1
    assert "17" in env["JAVA_HOME"]
