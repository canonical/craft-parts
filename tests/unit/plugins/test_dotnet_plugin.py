# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

import pytest
from pydantic import ValidationError

from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.dotnet_plugin import DotnetPlugin


@pytest.fixture
def dotnet_exe(new_dir):
    dotnet_bin = Path(new_dir, "mock_bin", "dotnet")
    dotnet_bin.parent.mkdir(exist_ok=True)
    dotnet_bin.write_text('#!/bin/sh\necho "6.0.0"')
    dotnet_bin.chmod(0o755)
    yield dotnet_bin


@pytest.fixture
def broken_dotnet_exe(new_dir):
    dotnet_bin = Path(new_dir, "mock_bin", "dotnet")
    dotnet_bin.parent.mkdir(exist_ok=True)
    dotnet_bin.write_text("#!/bin/sh\nexit 33")
    dotnet_bin.chmod(0o755)
    yield dotnet_bin


@pytest.fixture
def part_info(new_dir):
    yield PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dotnet_exe, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet_exe.parent)}"
    )
    validator.validate_environment()


def test_validate_environment_missing_dotnet(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "dotnet not found"


def test_validate_environment_broken_dotnet(broken_dotnet_exe, part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(broken_dotnet_exe.parent)}"
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "dotnet failed with error code 33"


def test_validate_environment_with_dotnet_part(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    validator.validate_environment(part_dependencies=["dotnet"])


def test_validate_environment_without_dotnet_part(part_info):
    properties = DotnetPlugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(part_name="my-part", env="PATH=/foo")
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "dotnet not found and part 'my-part' "
        "does not depend on a part named 'dotnet'"
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
    assert err[0]["type"] == "value_error.extra"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        DotnetPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "value_error.missing"
