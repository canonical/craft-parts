# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest

from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.bazel_plugin import BazelPlugin, BazelPluginProperties


@pytest.fixture
def plugin(new_dir):
    properties = BazelPluginProperties.unmarshal({
        "source": ".",
        "bazel-targets": ["//:hello_bazel"],
        "bazel-options": ["--copt=-O2"],
        "bazel-command": "build",
        # "bazel_startup_options": ["--max_idle_secs=5"]  # Uncomment if startup options are enabled
    })
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    return BazelPlugin(properties=properties, part_info=part_info)

def test_bazel_plugin_build_commands(plugin):
    commands = plugin.get_build_commands()
    assert len(commands) == 1
    cmd = commands[0]
    print(f'The command retrieved in build command is {cmd}')
    assert cmd.startswith("bazel ")
    assert "build" in cmd
    assert "--copt=-O2" in cmd
    assert "//:hello_bazel" in cmd

def test_bazel_plugin_test_command(new_dir):
    properties = BazelPluginProperties.unmarshal({
        "source": ".",
        "bazel-targets": ["//:my_test"],
        "bazel-options": ["--test_output=all"],
        "bazel-command": "test",
    })
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    plugin = BazelPlugin(properties=properties, part_info=part_info)
    commands = plugin.get_build_commands()
    print(f"Command in test command func is {commands}")
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd.startswith("bazel ")
    assert "test" in cmd
    assert "--test_output=all" in cmd
    assert "//:my_test" in cmd

def test_bazel_plugin_default_targets(new_dir):
    properties = BazelPluginProperties.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    plugin = BazelPlugin(properties=properties, part_info=part_info)
    commands = plugin.get_build_commands()
    assert len(commands) == 1
    cmd = commands[0]
    assert "bazel build" in cmd
    assert "//..." in cmd

def test_bazel_plugin_build_environment_proxies(monkeypatch, new_dir):
    # Set proxy variables in the environment
    monkeypatch.setenv("http_proxy", "http://proxy.example.com:3128")
    monkeypatch.setenv("https_proxy", "https://proxy.example.com:3129")
    monkeypatch.setenv("no_proxy", "localhost,127.0.0.1")
    properties = BazelPluginProperties.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    plugin = BazelPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert env["http_proxy"] == "http://proxy.example.com:3128"
    assert env["https_proxy"] == "https://proxy.example.com:3129"
    assert env["no_proxy"] == "localhost,127.0.0.1"

def test_bazel_plugin_build_environment_empty(monkeypatch, new_dir):
    # Ensure proxy variables are not set
    monkeypatch.delenv("http_proxy", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    properties = BazelPluginProperties.unmarshal({"source": "."})
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("foo", {}))
    plugin = BazelPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert env == {}