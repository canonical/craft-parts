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

"""The cargo-use plugin.

This plugin copy the content of the Rust repository to the local crates registry.
"""

import shutil
import sys
from typing import Literal

from overrides import override

from craft_parts import errors

from .base import Plugin
from .properties import PluginProperties

if sys.version_info >= (3, 11):
    import tomllib
else:
    # Python 3.10 compatibility
    import tomli as tomllib  # type: ignore[import-not-found]

CARGO_TOML_TEMPLATE = """\
[source.craft-parts]
directory = "{registry_dir}"

[source.apt]
directory = "/usr/share/cargo/registry"

[source.crates-io]
replace-with = "craft-parts"
"""


class CargoUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the cargo-use plugin."""

    plugin: Literal["cargo-use"] = "cargo-use"
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class CargoUsePlugin(Plugin):
    """Copy the content of the Rust repository and ."""

    properties_class = CargoUsePluginProperties

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
        registry_dir = (
            self._part_info.project_info.dirs.backstage_dir / "cargo-registry"
        )

        part_registry_target = (
            self._part_info.part_export_dir
            / "cargo-registry"
            / self._get_cargo_registry_dir_name()
        )
        if part_registry_target.exists():
            # as we don't track files we have to delete previous content
            # to avoid conflicts on rebuild
            shutil.rmtree(part_registry_target)
        part_registry_target.mkdir(parents=True)

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
            raise errors.PartsError(
                "Cannot use 'cargo-use' plugin on non-Rust project."
            )
        try:
            parsed_toml = tomllib.loads(cargo_toml.read_text())
        except tomllib.TOMLDecodeError as err:
            raise errors.PartsError(
                f"Cannot parse Cargo.toml for {self._part_info.part_name!r}"
            ) from err
        else:
            package_dict = parsed_toml.get("package")
            if not package_dict:
                raise errors.PartsError("Package section is missing in Cargo.toml file")
            package_name = package_dict.get("name", self._part_info.part_name)

            # according to the docs this field is optional since 1.7.5 and defaults to 0.0.0
            # it is required for publishing crates, so it should be available for most packages
            # https://doc.rust-lang.org/cargo/reference/manifest.html#the-version-field
            package_version = package_dict.get("version", "0.0.0")
            return f"{package_name}-{package_version}"
