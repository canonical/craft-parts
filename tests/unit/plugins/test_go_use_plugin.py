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


import subprocess

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.go_use_plugin import GoUsePlugin, _remove_local_replaces_cmd
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


def test_validate_environment(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", output="go version go1.17 linux/amd64")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_go(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'go' not found"


def test_validate_environment_broken_go(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'go' failed with error code 33"


def test_validate_environment_invalid_go(dependency_fixture, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)
    go = dependency_fixture("go", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(go.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid go compiler version ''"


def test_validate_environment_with_go_part(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["go-deps"])


def test_validate_environment_without_go_part(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'go' not found and part 'my-part' does not depend on a part named "
        "'go-deps' that would satisfy the dependency"
    )


def test_get_build_snaps(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()


def test_get_build_packages(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_packages() == set()


def test_get_build_environment(new_dir, part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_environment() == {}


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        GoUsePlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(part_info):
    properties = GoUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    assert plugin.get_out_of_source_build() is True


@pytest.mark.parametrize(
    "part_data", [{"source": "."}, {"source": ".", "source-subdir": "my/subdir"}]
)
def test_get_build_commands(mocker, part_info, part_data):
    """Test that go work is created and that work.go is created."""
    # Create a go.mod file
    part_info.part_src_subdir.mkdir(parents=True, exist_ok=True)
    (part_info.part_src_subdir / "go.mod").write_text(
        "module example.com/test\n\ngo 1.21\n"
    )

    properties = GoUsePlugin.properties_class.unmarshal(part_data)
    plugin = GoUsePlugin(properties=properties, part_info=part_info)

    dest_dir = part_info.part_export_dir / "go-use" / part_info.part_name
    go_mod_path = part_info.part_src_subdir / "go.mod"

    commands = plugin.get_build_commands()
    assert len(commands) == 3
    assert commands[0].startswith("awk ")
    assert str(go_mod_path) in commands[0]
    assert commands[1] == f"mkdir -p '{part_info.part_export_dir}/go-use'"
    assert commands[2] == f"ln -sf '{part_info.part_src_subdir}' '{dest_dir}'"


@pytest.mark.parametrize(
    ("input_content", "expected_content"),
    [
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n"
            ),
            id="no-replace-directives",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "replace example.com/foo => ./local\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "// replace example.com/foo => ./local\n"
            ),
            id="single-line-local-dot-slash",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace example.com/foo => ../sibling\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "// replace example.com/foo => ../sibling\n"
            ),
            id="single-line-local-dot-dot-slash",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace example.com/foo v1.2.3 => ./local\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "// replace example.com/foo v1.2.3 => ./local\n"
            ),
            id="single-line-local-with-version",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace example.com/foo => example.com/bar v1.0.0\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace example.com/foo => example.com/bar v1.0.0\n"
            ),
            id="single-line-non-local",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "replace (\n"
                "    example.com/foo => ./local\n"
                "    example.com/baz => ../other\n"
                ")\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "replace (\n"
                "// example.com/foo => ./local\n"
                "// example.com/baz => ../other\n"
                ")\n"
            ),
            id="block-all-local",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace (\n"
                "    example.com/foo => example.com/bar v1.0.0\n"
                ")\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "replace (\n"
                "    example.com/foo => example.com/bar v1.0.0\n"
                ")\n"
            ),
            id="block-all-non-local",
        ),
        pytest.param(
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "replace (\n"
                "    example.com/foo => ./local\n"
                "    example.com/bar => example.com/baz v1.0.0\n"
                ")\n"
            ),
            (
                "module example.com/mymod\n\n"
                "go 1.21\n\n"
                "require (\n"
                "    example.com/dep v1.0.0\n"
                ")\n\n"
                "replace (\n"
                "// example.com/foo => ./local\n"
                "    example.com/bar => example.com/baz v1.0.0\n"
                ")\n"
            ),
            id="block-mixed",
        ),
        pytest.param(
            ("module example.com/mymod\n\ngo 1.21\n\nreplace (\n)\n"),
            ("module example.com/mymod\n\ngo 1.21\n\nreplace (\n)\n"),
            id="block-empty",
        ),
    ],
)
def test_remove_local_replaces(tmp_path, input_content, expected_content):
    """Test that local replace directives are commented out."""
    go_mod = tmp_path / "go.mod"
    go_mod.write_text(input_content)

    cmd = _remove_local_replaces_cmd(go_mod)
    subprocess.run(["bash", "-c", cmd], check=True)

    assert go_mod.read_text() == expected_content
