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

import pathlib
import textwrap

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.cargo_use_plugin import CargoUsePlugin
from pydantic import ValidationError
from pyfakefs import fake_filesystem


@pytest.fixture
def fake_project_dir(fs: fake_filesystem.FakeFilesystem) -> pathlib.Path:
    project_dir = pathlib.Path("cargo-project")
    fs.create_dir(project_dir)
    return project_dir


@pytest.fixture
def part_info(fs: fake_filesystem.FakeFilesystem) -> PartInfo:
    fs.create_dir("cache")
    return PartInfo(
        project_info=ProjectInfo(
            application_name="test",
            cache_dir=pathlib.Path("cache"),
        ),
        part=Part("my-part", {}),
    )


@pytest.fixture
def project_name() -> str:
    return "craft-parts"


@pytest.fixture
def project_version() -> str:
    return "0.0.1"


@pytest.fixture
def fake_rust_project(
    part_info: PartInfo, project_name: str, project_version: str
) -> None:
    part_info.part_src_dir.mkdir(parents=True)
    project_file = part_info.part_src_dir / "Cargo.toml"
    project_file.write_text(
        textwrap.dedent(
            f"""\
            [package]
            name = "{project_name}"
            version = "{project_version}"
            """
        )
    )


@pytest.fixture
def plugin(part_info: PartInfo) -> CargoUsePlugin:
    properties = CargoUsePlugin.properties_class.unmarshal({"source": "."})
    return CargoUsePlugin(properties=properties, part_info=part_info)


def test_get_build_snaps(plugin: CargoUsePlugin):
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(plugin: CargoUsePlugin):
    assert plugin.get_build_packages() == set()


def test_get_build_environment(plugin: CargoUsePlugin):
    assert plugin.get_build_environment() == {}


def get_build_commands(target_directory: pathlib.Path) -> list[str]:
    return [f'cp --archive --link --no-dereference . "{target_directory}"']


@pytest.mark.usefixtures("fake_rust_project")
def test_get_build_commands(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
    project_name: str,
    project_version: str,
):
    cargo_registry_dir = (
        part_info.part_export_dir
        / "cargo-registry"
        / f"{project_name}-{project_version}"
    )

    assert not (part_info.work_dir / "cargo" / "config.toml").exists()

    assert plugin.get_build_commands() == get_build_commands(cargo_registry_dir)
    assert (
        part_info.work_dir / "cargo" / "config.toml"
    ).read_text() == textwrap.dedent(
        f"""\
        [source.craft-parts]
        directory = "{part_info.project_info.dirs.backstage_dir / "cargo-registry"}"

        [source.apt]
        directory = "/usr/share/cargo/registry"

        [source.crates-io]
        replace-with = "craft-parts"
        """
    )


@pytest.mark.usefixtures("fake_rust_project")
def test_get_build_commands_is_reentrant(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
    project_name: str,
    project_version: str,
):
    cargo_registry_dir = (
        part_info.part_export_dir
        / "cargo-registry"
        / f"{project_name}-{project_version}"
    )

    assert not (part_info.work_dir / "cargo" / "config.toml").exists()

    cargo_registry_dir.mkdir(parents=True)
    previous_file = cargo_registry_dir / "some_previous_file"
    previous_file.touch()

    assert plugin.get_build_commands() == get_build_commands(cargo_registry_dir)
    assert not previous_file.exists(), "Plugin should clean previous registry entry"


def test_get_build_commands_name_fallback(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
    project_version: str,
):
    part_info.part_src_dir.mkdir(parents=True)
    project_file = part_info.part_src_dir / "Cargo.toml"
    project_file.write_text(
        textwrap.dedent(
            f"""\
            [package]
            version = "{project_version}"
            """
        )
    )
    project_name = part_info.part_name

    cargo_registry_dir = (
        part_info.part_export_dir
        / "cargo-registry"
        / f"{project_name}-{project_version}"
    )

    assert not (part_info.work_dir / "cargo" / "config.toml").exists()

    assert plugin.get_build_commands() == get_build_commands(cargo_registry_dir)
    assert (part_info.work_dir / "cargo" / "config.toml").exists()


def test_get_build_commands_version_fallback(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
    project_name: str,
):
    part_info.part_src_dir.mkdir(parents=True)
    project_file = part_info.part_src_dir / "Cargo.toml"
    project_file.write_text(
        textwrap.dedent(
            f"""\
            [package]
            name = "{project_name}"
            """
        )
    )
    project_version = "0.0.0"

    cargo_registry_dir = (
        part_info.part_export_dir
        / "cargo-registry"
        / f"{project_name}-{project_version}"
    )

    assert not (part_info.work_dir / "cargo" / "config.toml").exists()

    assert plugin.get_build_commands() == get_build_commands(cargo_registry_dir)
    assert (part_info.work_dir / "cargo" / "config.toml").exists()


def test_get_build_commands_incorrect_cargo_toml(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
):
    part_info.part_src_dir.mkdir(parents=True)
    project_file = part_info.part_src_dir / "Cargo.toml"
    project_file.write_text("")

    with pytest.raises(
        errors.PartsError, match="Package section is missing in Cargo.toml file"
    ):
        plugin.get_build_commands()


def test_get_build_commands_non_parsable_cargo_toml(
    plugin: CargoUsePlugin,
    part_info: PartInfo,
):
    part_info.part_src_dir.mkdir(parents=True)
    project_file = part_info.part_src_dir / "Cargo.toml"
    project_file.write_text('{"i-am": "json"}')

    with pytest.raises(
        errors.PartsError, match="Cannot parse Cargo.toml for 'my-part'"
    ):
        plugin.get_build_commands()


def test_get_build_commands_missing_cargo_toml(
    plugin: CargoUsePlugin,
):
    with pytest.raises(
        errors.PartsError,
        match="Cannot use 'cargo-use' plugin on non-Rust project.",
    ):
        plugin.get_build_commands()


def test_invalid_parameters():
    with pytest.raises(ValidationError) as raised:
        CargoUsePlugin.properties_class.unmarshal(
            {"source": ".", "cargo-use-invalid": True}
        )
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("cargo-use-invalid",)
    assert err[0]["type"] == "extra_forbidden"


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        CargoUsePlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_out_of_source_build(plugin: CargoUsePlugin):
    assert plugin.get_out_of_source_build() is False
