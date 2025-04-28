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
from craft_parts.plugins.dotnet_v2_plugin import DotnetV2Plugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.mark.parametrize(
    "dotnet_version",
    [
        "8",
        "8.0",
        "9",
        "9.1",
        "10",
        "10.0",
    ],
)
def test_parameter_valid_dotnet_version(part_info, dotnet_version):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-version": dotnet_version}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    assert plugin


@pytest.mark.parametrize(
    "dotnet_version",
    [
        "8.",
        "8a",
        "0.8.0",
        "3.1",
        "abc",
        "9.1a",
    ],
)
def test_parameter_invalid_dotnet_version(dotnet_version):
    with pytest.raises(ValidationError) as raised:
        DotnetV2Plugin.properties_class.unmarshal(
            {"source": ".", "dotnet-version": dotnet_version}
        )

    assert raised


@pytest.mark.parametrize(
    "dotnet_verbosity",
    [
        "quiet",
        "q",
        "minimal",
        "m",
        "normal",
        "n",
        "detailed",
        "d",
        "diagnostic",
        "diag",
    ],
)
def test_parameter_valid_dotnet_verbosity(part_info, dotnet_verbosity):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-verbosity": dotnet_verbosity}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    assert plugin


@pytest.mark.parametrize("dotnet_verbosity", ["quietly", "invalid", "blah"])
def test_parameter_invalid_dotnet_verbosity(dotnet_verbosity):
    with pytest.raises(ValidationError) as raised:
        DotnetV2Plugin.properties_class.unmarshal(
            {"source": ".", "dotnet-verbosity": dotnet_verbosity}
        )

    assert raised


def test_validate_environment(dependency_fixture, part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)
    dotnet = dependency_fixture("dotnet")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_dotnet(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'dotnet' not found"


def test_validate_environment_broken_dotnet(dependency_fixture, part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)
    dotnet = dependency_fixture("dotnet", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(dotnet.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'dotnet' failed with error code 33"


def test_validate_environment_with_dotnet_part(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["dotnet-deps"])


def test_validate_environment_without_dotnet_part(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'dotnet' not found and part 'my-part' does not depend on a part named "
        "'dotnet-deps' that would satisfy the dependency"
    )


@pytest.mark.parametrize(
    ("dotnet_version", "expected_snap_name"),
    [
        ("8", "dotnet-sdk-80"),
        ("9", "dotnet-sdk-90"),
        ("8.0", "dotnet-sdk-80"),
        ("9.1", "dotnet-sdk-91"),
        ("10.0", "dotnet-sdk-100"),
    ],
)
def test_get_build_snaps(part_info, dotnet_version, expected_snap_name):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-version": dotnet_version}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == {expected_snap_name}


def test_get_build_packages(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


@pytest.mark.parametrize("part_version", ["8", "8.0", "9", "9.1", "10"])
def test_get_build_environment_without_dotnet_deps_and_valid_versions(
    part_info, part_version
):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-version": part_version}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    environment = plugin.get_build_environment()
    assert len(environment) == 3
    assert environment["DOTNET_NOLOGO"] == "1"
    assert "LD_LIBRARY_PATH" in environment
    assert "PATH" in environment


def test_get_build_commands_default_values(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


@pytest.mark.parametrize("configuration", ["Debug", "Release"])
def test_get_build_commands_configuration(part_info, configuration):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-configuration": configuration}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            f"--configuration {configuration}",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            f"--configuration {configuration}",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


def test_get_build_commands_project(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-project": "myproject.csproj"}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        [
            "dotnet",
            "restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "myproject.csproj",
        ],
    )
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
            "myproject.csproj",
        ],
    )
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
            "myproject.csproj",
        ],
    )
    assert build_commands[2].strip() == ""


def test_get_build_commands_properties(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-properties": {"foo": "bar"}}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        [
            "dotnet",
            "restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "-p:foo=bar",
        ],
    )
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
            "-p:foo=bar",
        ],
    )
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
            "-p:foo=bar",
        ],
    )
    assert build_commands[2].strip() == ""


@pytest.mark.parametrize("self_contained", [True, False])
def test_get_build_commands_self_contained(part_info, self_contained):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-self-contained": self_contained}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            f"--self-contained {self_contained}",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            f"--self-contained {self_contained}",
        ],
    )
    assert build_commands[2] == ""


@pytest.mark.parametrize(
    "verbosity",
    [
        "quiet",
        "q",
        "minimal",
        "m",
        "normal",
        "n",
        "detailed",
        "d",
        "diagnostic",
        "diag",
    ],
)
def test_get_build_commands_valid_verbosity(part_info, verbosity):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-verbosity": verbosity}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", f"--verbosity {verbosity}", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            f"--verbosity {verbosity}",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            f"--verbosity {verbosity}",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


@pytest.mark.parametrize(
    "part_version",
    [
        "8",
        "8.0",
        "9.1",
    ],
)
def test_get_build_commands_valid_version(part_info, part_version):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-version": part_version}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


def test_get_build_commands_restore_properties(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-restore-properties": {"foo": "bar"}}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        [
            "dotnet",
            "restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "-p:foo=bar",
        ],
    )
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2].strip() == ""


def test_get_build_commands_restore_sources(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-restore-sources": ["source1", "source2"]}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        [
            "dotnet",
            "restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--source source1",
            "--source source2",
        ],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


def test_get_build_commands_build_framework(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-build-framework": "net8.0"}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--framework net8.0",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


def test_get_build_commands_restore_configfile(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-restore-configfile": "configfile"}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        [
            "dotnet",
            "restore",
            "--configfile configfile",
            "--verbosity normal",
            "--runtime linux-x64",
        ],
    )
    assert build_commands[0] == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1] == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2] == ""


def test_get_build_commands_build_properties(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-build-properties": {"foo": "bar"}}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
            "-p:foo=bar",
        ],
    )
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[2].strip() == ""


def test_get_build_commands_publish_properties(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal(
        {"source": ".", "dotnet-publish-properties": {"foo": "bar"}}
    )
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    build_commands = plugin.get_build_commands()
    assert len(build_commands) == 3

    build_commands[0] = _remove_parameter_from_command(
        build_commands[0],
        ["dotnet", "restore", "--verbosity normal", "--runtime linux-x64"],
    )
    assert build_commands[0].strip() == ""

    build_commands[1] = _remove_parameter_from_command(
        build_commands[1],
        [
            "dotnet",
            "build",
            "--configuration Release",
            "--no-restore",
            "--verbosity normal",
            "--runtime linux-x64",
            "--self-contained False",
        ],
    )
    assert build_commands[1].strip() == ""

    build_commands[2] = _remove_parameter_from_command(
        build_commands[2],
        [
            "dotnet",
            "publish",
            "--configuration Release",
            f"--output {plugin._part_info.part_install_dir}",
            "--verbosity normal",
            "--no-restore",
            "--no-build",
            "--runtime linux-x64",
            "--self-contained False",
            "-p:foo=bar",
        ],
    )
    assert build_commands[2].strip() == ""


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        DotnetV2Plugin.properties_class.unmarshal(
            {"source": ".", "dotnet-invalid": True}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("dotnet-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        DotnetV2Plugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(part_info):
    properties = DotnetV2Plugin.properties_class.unmarshal({"source": "."})
    plugin = DotnetV2Plugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is False


def _remove_parameter_from_command(command: str, parameters: list[str]) -> str:
    for parameter in parameters:
        assert parameter in command
        command = command.replace(parameter, "").strip()
    return command
