# Copyright 2026 Canonical Ltd.
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
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""The Zig plugin's public configuration and execution contract."""

import subprocess
from pathlib import Path

import pytest
from craft_parts import errors, plugins
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.zig_plugin import ZigPlugin, ZigPluginProperties
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def make_plugin(part_info, **options):
    properties = ZigPluginProperties.unmarshal({"source": ".", **options})
    return ZigPlugin(properties=properties, part_info=part_info)


def test_defaults(part_info):
    plugin = make_plugin(part_info)
    assert plugins.get_plugin_class("zig") is ZigPlugin
    assert plugin.get_build_packages() == set()
    assert plugin.get_build_snaps() == {"zig/latest/beta"}
    assert plugin.get_pull_commands() == []
    assert not plugin.get_out_of_source_build()
    properties = ZigPluginProperties(source=".")
    assert properties.zig_build_parameters == []
    assert properties.zig_install_prefix == "/"


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"source": ".", "zig-unknown": True},
        {"source": ".", "zig-build-parameters": "-Dfoo"},
        {"source": ".", "zig-build-parameters": [42]},
    ],
)
def test_invalid_properties(data):
    with pytest.raises(ValidationError):
        ZigPluginProperties.unmarshal(data)


@pytest.mark.parametrize("prefix", ["usr", "", "/../tmp", "/usr/../../tmp", "/usr\x00"])
def test_invalid_prefix(prefix):
    with pytest.raises(ValidationError, match="absolute path"):
        ZigPluginProperties.unmarshal({"source": ".", "zig-install-prefix": prefix})


def test_zig_deps_replaces_snap(part_info):
    plugin = make_plugin(part_info, after=["zig-deps"])
    assert plugin.get_build_snaps() == set()


def test_change_tracking():
    assert ZigPluginProperties.get_pull_properties() == []
    assert {"zig-build-parameters", "zig-install-prefix"} <= set(
        ZigPluginProperties.get_build_properties()
    )


def test_build_environment(part_info):
    env = make_plugin(part_info).get_build_environment()
    assert "PATH" not in env
    assert env["ZIG_GLOBAL_CACHE_DIR"] == str(
        part_info.part_cache_dir / "zig" / "global"
    )
    assert env["ZIG_LOCAL_CACHE_DIR"] == str(part_info.part_build_dir / ".zig-cache")


def test_caches_are_private_to_each_part(part_info):
    other_info = PartInfo(
        project_info=part_info.project_info,
        part=Part("other-part", {}),
    )
    first = make_plugin(part_info).get_build_environment()
    second = make_plugin(other_info).get_build_environment()
    assert first["ZIG_GLOBAL_CACHE_DIR"] != second["ZIG_GLOBAL_CACHE_DIR"]


def test_build_arguments_are_literal(part_info, tmp_path):
    arguments = [
        "-Dmessage=hello world",
        "-Drpath=$ORIGIN/../lib",
        "-Dvalue=$(touch injected)",
        "-Dquote=a'b",
    ]
    plugin = make_plugin(
        part_info, **{"zig-build-parameters": arguments, "zig-install-prefix": "/usr"}
    )
    (part_info.stage_dir / "usr").mkdir(parents=True)
    # Capture the shell's actual argv, rather than only checking generated quoting.
    zig = tmp_path / "zig"
    zig.write_text('#!/bin/sh\nprintf \'%s\\n\' "$DESTDIR" "$@"\n')
    zig.chmod(0o755)
    result = subprocess.check_output(
        ["/bin/bash", "-c", "\n".join(plugin.get_build_commands())],
        env={"PATH": str(tmp_path)},
        text=True,
    ).splitlines()
    assert result[:5] == [
        str(part_info.part_install_dir),
        "build",
        "install",
        "--prefix",
        "/usr",
    ]
    assert f"-j{part_info.parallel_build_count}" in result
    assert str(part_info.stage_dir) in result
    assert str(part_info.stage_dir / "usr") in result
    assert result[-len(arguments) :] == arguments
    assert not Path("injected").exists()


def test_missing_stage_prefixes_are_omitted(part_info):
    assert "--search-prefix" not in make_plugin(part_info).get_build_commands()[0]


@pytest.mark.parametrize("version", ["0.11.0", "0.14.1", "0.15.0-dev.1+abcdef"])
def test_final_validation(part_info, dependency_fixture, version):
    plugin = make_plugin(part_info)
    zig = dependency_fixture("zig", output=version)
    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={zig.parent}", properties=plugin._options
    )
    validator.validate_environment()


def test_external_dependency_deferral(part_info):
    plugin = make_plugin(part_info)
    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/missing", properties=plugin._options
    )
    validator.validate_environment(part_dependencies=["zig-deps"])
    with pytest.raises(errors.PluginEnvironmentValidationError, match="zig-deps"):
        validator.validate_environment(part_dependencies=[])
    with pytest.raises(errors.PluginEnvironmentValidationError, match="not found"):
        validator.validate_environment()


@pytest.mark.parametrize(
    ("output", "reason"),
    [("0.10.1", "older than"), ("not zig", "invalid Zig compiler version")],
)
def test_dependency_replaces_unsupported_compiler(
    part_info, dependency_fixture, output, reason
):
    plugin = make_plugin(part_info, after=["zig-deps"])
    zig = dependency_fixture("zig", output=output)
    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={zig.parent}", properties=plugin._options
    )

    validator.validate_environment(part_dependencies=["zig-deps"])
    for dependencies in ([], ["other-part"], None):
        with pytest.raises(errors.PluginEnvironmentValidationError, match=reason):
            validator.validate_environment(part_dependencies=dependencies)

    dependency_fixture("zig", output="0.14.1")
    validator.validate_environment()


@pytest.mark.parametrize(
    "output", ["zig 0.14.1", "not zig", "0.14", "0.\u0661\u0664.1"]
)
def test_invalid_compiler_version(part_info, dependency_fixture, output):
    plugin = make_plugin(part_info)
    zig = dependency_fixture("zig", output=output)
    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={zig.parent}", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError, match="version"):
        validator.validate_environment()


@pytest.mark.parametrize("output", ["0.10.1", "0.10.0-dev.4+abcdef"])
def test_compiler_without_parallel_build_option(part_info, dependency_fixture, output):
    plugin = make_plugin(part_info)
    zig = dependency_fixture("zig", output=output)
    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={zig.parent}", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError, match="older than"):
        validator.validate_environment()


def test_broken_compiler_not_deferred(part_info, dependency_fixture):
    plugin = make_plugin(part_info)
    zig = dependency_fixture("zig", broken=True)
    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={zig.parent}", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError, match="error code 33"):
        validator.validate_environment(part_dependencies=["zig-deps"])
