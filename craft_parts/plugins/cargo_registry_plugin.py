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

"""The cargo-registry plugin.

This plugin copy the content of the Rust repository to the interminient registry.
"""

from typing import Literal

import tomli
from overrides import override

from .base import Plugin
from .properties import PluginProperties

CARGO_TOML_TEMPLATE = """
[source.craft-parts]
directory = "{registry_dir}"

[source.apt]
directory = "/usr/share/cargo/registry"

[source.crates-io]
replace-with = "craft-parts"
"""


class CargoRegistryPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the cargo-registry plugin."""

    plugin: Literal["cargo-registry"] = "cargo-registry"
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class CargoRegistryPlugin(Plugin):
    """Copy the content of the Rust repository and ."""

    properties_class = CargoRegistryPluginProperties

    # to check with the team
    # supports_strict_mode = True  # noqa: ERA001

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list commands to retrieve dependencies during the pull step."""
        return []

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        workspace_dir = self._part_info.project_info.dirs.parts_dir
        registry_dir = workspace_dir / "cargo-registry-craft-parts"
        registry_dir.mkdir(exist_ok=True)

        part_registry_target = registry_dir / self._get_cargo_registry_dir_name()
        part_registry_target.mkdir(exist_ok=True)

        cargo_config = self._part_info.work_dir / "cargo/config.toml"
        if not cargo_config.exists():
            cargo_config.parent.mkdir(exist_ok=True, parents=True)
            cargo_config.write_text(
                CARGO_TOML_TEMPLATE.format(registry_dir=registry_dir)
            )

        checksum_file = part_registry_target / ".cargo-checksum.json"

        if not checksum_file.exists():
            # create checksum_file
            checksum_file.write_text('{"files":{}}')

        return [f'cp --archive --link --no-dereference . "{part_registry_target}"']

    def _get_cargo_registry_dir_name(self) -> str:
        """Create a name for the cargo-registry directory based on Cargo.toml."""
        cargo_toml = self._part_info.part_src_subdir / "Cargo.toml"
        if not cargo_toml.exists():
            # to update
            raise RuntimeError(
                "Cannot use 'cargo-registry' plugin on non-Rust project."
            )
        try:
            parsed_toml = tomli.loads(cargo_toml.read_text())
        except tomli.TOMLDecodeError as err:
            # to update
            raise RuntimeError(
                f"Cannot parse Cargo.toml for {self._part_info.part_name!r}"
            ) from err
        else:
            package_dict = parsed_toml.get("package")
            if not package_dict:
                # to update
                raise RuntimeError("Package section is missing in Cargo.toml file")
            package_name = package_dict.get("name", self._part_info.part_name)
            package_version = package_dict.get("version")
            return (
                f"{package_name}-{package_version}" if package_version else package_name
            )
