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
from craft_parts.plugins.cargo_package_plugin import (
    CargoPackagePlugin,
    CargoPackagePluginProperties,
)


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture(params=[[], ["edge", "corner"]])
def features(request):
    return request.param


@pytest.fixture(params=["cargo", "cargo-123.456"])
def cargo_command(request):
    return request.param


@pytest.fixture
def properties(features, cargo_command) -> CargoPackagePluginProperties:
    return CargoPackagePluginProperties.unmarshal(
        {
            "source": ".",
            "cargo-package-features": features,
            "cargo-package-cargo-command": cargo_command,
        }
    )


@pytest.fixture
def plugin(part_info, properties) -> CargoPackagePlugin:
    return CargoPackagePlugin(properties=properties, part_info=part_info)


def test_get_build_snaps(plugin):
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(plugin):
    assert plugin.get_build_packages() == set()


def test_get_build_environment(plugin):
    assert plugin.get_build_environment() == {}


def test_get_package_command(plugin, cargo_command, features):
    command = plugin._get_package_command()
    assert command.startswith(f"{cargo_command} ")
    if features:
        for feature in features:
            assert feature in command
    else:
        assert "--features" not in command


def test_get_build_commands(plugin):
    commands = plugin.get_build_commands()
    assert 'echo \'{"files":{}}\' > "$package/.cargo-checksum.json"' in commands[1]
