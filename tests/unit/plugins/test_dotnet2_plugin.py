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
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.dotnet2_plugin import Dotnet2Plugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal({"source": "."})
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)
    dotnet = dependency_fixture("dotnet")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet.parent)}", properties=properties
    )
    validator.validate_environment()


@pytest.mark.parametrize("dotnet_version, expected_snap_name", [
    ("8", "dotnet-sdk-80"),
    ("9", "dotnet-sdk-90"),
    ("8.0", "dotnet-sdk-80"),
    ("9.1", "dotnet-sdk-91"),
    ("10.0", "dotnet-sdk-100"),
])
def test_get_build_snaps(part_info, dotnet_version, expected_snap_name):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {
            "source": ".",
            "dotnet2-version": dotnet_version
        })
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == {expected_snap_name}


def test_get_build_packages(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal({"source": "."})
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {
            "source": ".",
            "dotnet2-version": "8.0"
        })
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    environment = plugin.get_build_environment()
    assert len(environment) >= 2
    assert environment["DOTNET_NOLOGO"] == "1"
    assert "LD_LIBRARY_PATH" in environment


def test_get_build_commands_default_values(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal({"source": "."})
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path, "restore", "--verbosity normal", "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


@pytest.mark.parametrize("configuration", [
    "Debug",
    "Release"
])
def test_get_build_commands_configuration(part_info, configuration):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-configuration": configuration}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        f"--configuration {configuration}",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        f"--configuration {configuration}",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


def test_get_build_commands_project(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-project": "myproject.csproj"}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "myproject.csproj"
    ])
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False",
        "myproject.csproj"
    ])
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False",
        "myproject.csproj"
    ])
    assert build_commands[2].strip() == ""


@pytest.mark.parametrize("self_contained", [
    True,
    False
])
def test_get_build_commands_self_contained(part_info, self_contained):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-self-contained": self_contained}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        f"--self-contained {self_contained}"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        f"--self-contained {self_contained}"
    ])
    assert build_commands[2] == ""


@pytest.mark.parametrize("verbosity", [
    "quiet",
    "q",
    "minimal",
    "m",
    "normal",
    "n",
    "detailed",
    "d",
    "diagnostic",
    "diag"
])
def test_get_build_commands_valid_verbosity(part_info, verbosity):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-verbosity": verbosity}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        f"--verbosity {verbosity}",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        f"--verbosity {verbosity}",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        f"--verbosity {verbosity}",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


def test_get_build_commands_invalid_verbosity(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-verbosity": "invalid"}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    with pytest.raises(ValueError) as raised:
        plugin.get_build_commands()

    assert str(raised.value) == "Invalid verbosity level"


@pytest.mark.parametrize("part_version, snap_version", [
    ( "8", "80" ),
    ( "8.0", "80" ),
    ( "9.1", "91" ),
])
def test_get_build_commands_valid_version(part_info, part_version, snap_version):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-version": part_version}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = f"/snap/dotnet-sdk-{snap_version}/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


@pytest.mark.parametrize("part_version", [
    "2",
    "2.2",
    "3",
    "3.1",
    "5",
    "5.0",
    "5.1",
])
def test_get_build_commands_invalid_version(part_info, part_version):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet2-version": part_version}
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    with pytest.raises(ValueError) as raised:
        plugin.get_build_commands()

    assert str(raised.value) == "Version must be greater or equal to 6.0"


def test_get_build_commands_restore_sources(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {
            "source": ".",
            "dotnet2-restore-sources": ["source1", "source2"]
        }
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--source source1",
        "--source source2"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


def test_get_build_commands_restore_configfile(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {
            "source": ".",
            "dotnet2-restore-configfile": "configfile"
        }
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--configfile configfile",
        "--verbosity normal",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


def test_get_build_commands_build_framework(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal(
        {
            "source": ".",
            "dotnet2-build-framework": "net8.0"
        }
    )
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    default_snap_path = "/snap/dotnet-sdk-80/current/usr/lib/dotnet/dotnet"

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_commands_from_string(build_commands[0], [
        default_snap_path,
        "restore",
        "--verbosity normal",
        "--runtime linux-x64"
    ])
    assert build_commands[0] == ""

    build_commands[1] = _remove_commands_from_string(build_commands[1], [
        default_snap_path,
        "build",
        "--configuration Release",
        "--no-restore",
        "--framework net8.0",
        "--verbosity normal",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[1] == ""

    build_commands[2] = _remove_commands_from_string(build_commands[2], [
        default_snap_path,
        "publish",
        "--configuration Release",
        f"--output {plugin._part_info.part_install_dir}",
        "--verbosity normal",
        "--no-restore",
        "--no-build",
        "--runtime linux-x64",
        "--self-contained False"
    ])
    assert build_commands[2] == ""


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        Dotnet2Plugin.properties_class.unmarshal({"source": ".", "dotnet2-invalid": True})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("dotnet2-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        Dotnet2Plugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(part_info):
    properties = Dotnet2Plugin.properties_class.unmarshal({"source": "."})
    plugin = Dotnet2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False


def _remove_commands_from_string(string: str, commands: list[str]) -> str:
    for command in commands:
        string = string.replace(command, "")
    return string.strip()
