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
import subprocess

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.ruby_plugin import RubyPlugin


@pytest.fixture
def part_info_with_dependency(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"after": ["ruby-deps"]}),
    )


@pytest.fixture
def part_info_without_dependency(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_get_build_packages_after_rubu_deps(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)
    assert plugin.get_build_packages() == set()


def test_get_build_packages_no_ruby_deps(part_info_without_dependency):
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_without_dependency)
    assert plugin.get_build_packages() == {"curl", "libssl-dev"}


def test_get_build_environment(part_info_with_dependency):
    expected_env = {
        "PATH": f"${{CRAFT_PART_INSTALL}}/usr/bin:${{PATH}}",
        "GEM_HOME": "${CRAFT_PART_INSTALL}",
        "GEM_PATH": "${CRAFT_PART_INSTALL}",
    }
    properties = RubyPlugin.properties_class.unmarshal({"source": "."})
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    assert plugin.get_build_environment() == expected_env


def test_pull_build_commands_after_ruby_deps(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": "."}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    pull_commands = plugin.get_pull_commands()
    assert len(pull_commands) == 0

    build_commands = plugin.get_pull_commands()
    assert len(build_commands) == 0


def test_pull_build_commands_no_ruby_deps(part_info_without_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": "."}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_without_dependency)

    pull_commands = plugin.get_pull_commands()
    assert len(pull_commands) > 0
    assert (
        "curl -L --proto '=https' --tlsv1.2 "
        "https://github.com/postmodern/ruby-install/archive/refs/tags/v0.10.1.tar.gz "
        "-o ruby-install.tar.gz"
    ) in pull_commands

    build_commands = plugin.get_build_commands()
    assert len(build_commands) > 0
    assert (
        "ruby-install-0.10.1/bin/ruby-install --src-dir ${CRAFT_PART_SRC} "
        "--install-dir ${CRAFT_PART_INSTALL}/usr --package-manager apt "
        "--jobs=${CRAFT_PARALLEL_BUILD_COUNT} ruby-3.2 -- "
        "--without-baseruby --enable-load-relative --disable-install-doc"
    ) in build_commands


def test_ruby_gem_install(part_info_with_dependency):
    properties = RubyPlugin.properties_class.unmarshal(
        {"source": ".", "ruby-gems": ["mygem1", "mygem2"]}
    )
    plugin = RubyPlugin(properties=properties, part_info=part_info_with_dependency)

    build_commands = plugin.get_build_commands()
    assert build_commands[-1] == "gem install --env-shebang --no-document mygem1 mygem2"