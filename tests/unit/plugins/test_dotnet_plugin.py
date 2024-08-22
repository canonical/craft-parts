# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.dotnet_plugin import DotnetPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)
    dotnet = dependency_fixture("dotnet")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_dotnet(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'dotnet' not found"


def test_validate_environment_broken_dotnet(dependency_fixture, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)
    dotnet = dependency_fixture("dotnet", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'dotnet' failed with error code 33"


def test_validate_environment_with_dotnet_part(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["dotnet-deps"])


def test_validate_environment_without_dotnet_part(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'dotnet' not found and part 'my-part' does not depend on a part named "
        "'dotnet-deps' that would satisfy the dependency"
    )


def test_get_build_snaps(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(new_dir, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_get_build_commands(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "dotnet build -c Release",
        f"dotnet publish -c Release -o {plugin._part_info.part_install_dir}",
    ]


def test_get_build_commands_self_contained(part_info):
    properties = DotnetPlugin.properties_class.unmarshal(
        {"source": ".", "dotnet-self-contained-runtime-identifier": "linux-x64"}
    )
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == [
        "dotnet build -c Release",
        f"dotnet publish -c Release -o {plugin._part_info.part_install_dir} "
        "--self-contained -r linux-x64",
    ]


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        DotnetPlugin.properties_class.unmarshal({"source": ".", "dotnet-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("dotnet-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        DotnetPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(new_dir, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False
