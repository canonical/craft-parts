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
from craft_parts.plugins.bazel_plugin import BazelPlugin, BazelPluginProperties


@pytest.fixture
def plugin(new_dir):
    properties = BazelPluginProperties(
        source=".",
        bazel_targets=["//:hello_bazel"],
        bazel_startup_options=["--max_idle_secs=5"],
        bazel_build_options=["--copt=-O2"]
    )
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    return BazelPlugin(properties=properties, part_info=part_info)

def test_bazel_plugin_build_commands(plugin):
    commands = plugin.get_build_commands()
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd.startswith("bazel ")
    assert "build" in cmd
    assert "--max_idle_secs=5" in cmd
    assert "--copt=-O2" in cmd
    assert "//:hello_bazel" in cmd

def test_bazel_plugin_empty_targets(new_dir):
    properties = BazelPluginProperties(source=".")
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    plugin = BazelPlugin(properties=properties, part_info=part_info)
    commands = plugin.get_build_commands()
    assert len(commands) == 1
    cmd = commands[0]
    assert "bazel build" in cmd
    # Should not have '--' or targets if none specified
    assert "-- " not in cmd 