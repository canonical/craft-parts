# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
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
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import shlex
from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.fpc_plugin import FpcPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def plugin(part_info):
    properties = FpcPlugin.properties_class.unmarshal(
        {"source": ".", "fpc-programs": ["src/hello.pas"]}
    )
    return FpcPlugin(properties=properties, part_info=part_info)


def test_validate_environment(dependency_fixture, part_info, plugin):
    fpc = dependency_fixture("fpc", output="3.2.2")

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(fpc.parent)}", properties=plugin._options
    )
    validator.validate_environment()


def test_validate_environment_missing_fpc(plugin):
    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'fpc' not found"


def test_validate_environment_broken_fpc(dependency_fixture, plugin):
    fpc = dependency_fixture("fpc", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(fpc.parent)}", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'fpc' failed with error code 33"


def test_validate_environment_invalid_fpc(dependency_fixture, plugin):
    fpc = dependency_fixture("fpc", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(fpc.parent)}", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid fpc compiler version ''"


def test_validate_environment_with_fpc_part(plugin):
    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=plugin._options
    )
    validator.validate_environment(part_dependencies=["fpc-deps"])


def test_validate_environment_without_fpc_part(plugin):
    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=plugin._options
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'fpc' not found and part 'my-part' does not depend on a part named "
        "'fpc-deps' that would satisfy the dependency"
    )


def test_get_build_snaps(plugin):
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(plugin):
    assert plugin.get_build_packages() == set()


def test_get_build_environment(plugin):
    assert plugin.get_build_environment() == {}


def test_get_out_of_source_build(plugin):
    assert plugin.get_out_of_source_build() is False


def test_get_build_commands(part_info, plugin):
    unit_dir = part_info.part_build_subdir / ".parts" / "units"
    bin_dir = part_info.part_install_dir / "bin"

    assert plugin.get_build_commands() == [
        f"mkdir -p {unit_dir} {bin_dir}",
        f"fpc -FU{unit_dir} -FE{bin_dir} src/hello.pas",
    ]


def test_get_build_commands_with_options(part_info):
    properties = FpcPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "fpc-programs": ["src/hello.pas", "src/goodbye.pas"],
            "fpc-unit-paths": ["units", "lib/*"],
            "fpc-include-paths": ["include"],
            "fpc-parameters": ["-O2", "-dLOUD"],
        }
    )
    plugin = FpcPlugin(properties=properties, part_info=part_info)
    unit_dir = part_info.part_build_subdir / ".parts" / "units"
    bin_dir = part_info.part_install_dir / "bin"
    compiler = (
        f"fpc -Fuunits -Fu'lib/*' -Fiinclude -FU{unit_dir} -FE{bin_dir} -O2 -dLOUD"
    )

    assert plugin.get_build_commands() == [
        f"mkdir -p {unit_dir} {bin_dir}",
        f"{compiler} src/hello.pas",
        f"{compiler} src/goodbye.pas",
    ]


def test_get_build_commands_quoting(part_info):
    """Paths are quoted so the shell passes them to the compiler verbatim."""
    properties = FpcPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "fpc-programs": ["my programs/hello.pas"],
            "fpc-unit-paths": ["my units", "$special/units"],
            "fpc-include-paths": ["inc;dir"],
        }
    )
    plugin = FpcPlugin(properties=properties, part_info=part_info)
    unit_dir = shlex.quote(str(part_info.part_build_subdir / ".parts" / "units"))
    bin_dir = shlex.quote(str(part_info.part_install_dir / "bin"))

    assert plugin.get_build_commands() == [
        f"mkdir -p {unit_dir} {bin_dir}",
        (
            f"fpc -Fu'my units' -Fu'$special/units' -Fi'inc;dir' -FU{unit_dir} "
            f"-FE{bin_dir} 'my programs/hello.pas'"
        ),
    ]


def test_get_build_commands_source_subdir(new_dir):
    part_info = PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part(
            "my-part", {"plugin": "fpc", "source": ".", "source-subdir": "pascal"}
        ),
    )
    properties = FpcPlugin.properties_class.unmarshal(
        {"source": ".", "fpc-programs": ["hello.pas"]}
    )
    plugin = FpcPlugin(properties=properties, part_info=part_info)

    unit_dir = Path(part_info.part_build_dir, "pascal", ".parts", "units")
    assert plugin.get_build_commands()[0].startswith(f"mkdir -p {unit_dir}")


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        FpcPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 2
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"
    assert err[1]["loc"] == ("fpc-programs",)
    assert err[1]["type"] == "missing"


def test_empty_programs():
    with pytest.raises(ValidationError) as raised:
        FpcPlugin.properties_class.unmarshal({"source": ".", "fpc-programs": []})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("fpc-programs",)
    assert err[0]["type"] == "too_short"


def test_duplicate_programs():
    with pytest.raises(ValidationError) as raised:
        FpcPlugin.properties_class.unmarshal(
            {"source": ".", "fpc-programs": ["hello.pas", "hello.pas"]}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("fpc-programs",)
    assert "Duplicate values in list: ['hello.pas']" in err[0]["msg"]


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        FpcPlugin.properties_class.unmarshal(
            {"source": ".", "fpc-programs": ["hello.pas"], "fpc-invalid": True}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("fpc-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_get_build_commands_with_dependencies(new_dir):
    """Search paths exported by fpc-use parts in `after` are passed to the compiler."""
    part_info = PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"after": ["greetlib", "not-fpc-use"]}),
    )
    export_dir = part_info.backstage_dir / "fpc-use" / "greetlib"
    export_dir.mkdir(parents=True)
    (export_dir / "unit-paths").write_text("units\nlib/*\n")
    (export_dir / "include-paths").write_text("include\n")

    properties = FpcPlugin.properties_class.unmarshal(
        {"source": ".", "fpc-programs": ["src/hello.pas"], "fpc-unit-paths": ["own"]}
    )
    plugin = FpcPlugin(properties=properties, part_info=part_info)
    unit_dir = part_info.part_build_subdir / ".parts" / "units"
    bin_dir = part_info.part_install_dir / "bin"
    source = export_dir / "source"

    assert plugin.get_build_commands() == [
        f"mkdir -p {unit_dir} {bin_dir}",
        (
            f"fpc -Fuown -Fu{source}/units -Fu'{source}/lib/*' "
            f"-Fi{source}/include -FU{unit_dir} -FE{bin_dir} src/hello.pas"
        ),
    ]
