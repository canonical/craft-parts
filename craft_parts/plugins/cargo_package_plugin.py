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

"""A plugin for packaging rust crates and publishing them to a local registry.."""

import logging
import pathlib
import textwrap
from typing import Literal, cast

import pydantic
from overrides import override

from craft_parts.constraints import UniqueList

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)

CARGO_TOML_TEMPLATE = """
[net]
offline = true

[source.craft-parts]
directory = "{registry_dir}"

[source.apt]
directory = "/usr/share/cargo/registry"

[source.crates-io]
replace-with = "craft-parts"
"""


class CargoPackagePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the cargo-package plugin."""

    plugin: Literal["cargo-package"] = "cargo-package"

    # part properties required by the plugin
    cargo_package_features: UniqueList[str] = pydantic.Field(default_factory=list)
    cargo_package_cargo_command: str = "cargo"
    source: str  # pyright: ignore[reportGeneralTypeIssues]
    after: UniqueList[str] | None = None


class CargoPackagePluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Validate the environment for the cargo package plugin."""

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build crates.

        :param part_dependencies: A list of the parts this part depends on.
        """
        options = cast(CargoPackagePluginProperties, self._options)
        if "rust-deps" in (part_dependencies or []):
            # If we have a rust-deps dependency, we don't need to check for cargo.
            return

        self.validate_dependency(
            dependency=options.cargo_package_cargo_command,
            plugin_name=options.plugin,
            part_dependencies=part_dependencies,
        )


class CargoPackagePlugin(Plugin):
    """Build a Cargo crate and publish it to a local directory registry."""

    properties_class = CargoPackagePluginProperties
    validator_class = CargoPackagePluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @property
    def _registry_dir(self) -> pathlib.Path:
        return self._part_info.project_info.dirs.stage_dir / "cargo_registry"

    @property
    def _registry_output_dir(self) -> pathlib.Path:
        return self._part_info.part_install_dir / "cargo_registry"

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def _get_package_command(self) -> str:
        options = cast(CargoPackagePluginProperties, self._options)
        cargo = options.cargo_package_cargo_command
        features = ",".join(options.cargo_package_features)
        if features:
            features = f"--features {features}"
        return f"{cargo} package --no-verify {features}"

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        # We do not want this implementation detail exposed in the run script
        # This sets the default registry for all parts to use.
        cargo_config = pathlib.Path("~/.cargo/config.toml").expanduser().resolve()
        if not cargo_config.exists():
            cargo_config.parent.mkdir(exist_ok=True, parents=True)
            cargo_config.write_text(
                CARGO_TOML_TEMPLATE.format(registry_dir=self._registry_dir)
            )

        # This is a bit hard to read as it's a combination of pythonisms and bashisms.
        # What we're doing here is creating a bash clause that looks up the value
        # of the CARGO_REGISTRY_DIRECTORY environment variable and, if it's not
        # assigned, uses the plugin's default registry_output_dir. This way,
        # the user can replace the registry directory if they want. For example,
        # to use the Debian cargo registry at /usr/share/cargo/registry, they
        # can set CARGO_REGISTRY_DIRECTORY=/usr/share/cargo/registry and then in
        # all other parts set the cargo config environment variable
        # CARGO_REGISTRY_DEFAULT to the value "apt"
        write_registry_bash = (
            f"${{CARGO_REGISTRY_DIRECTORY:-{self._registry_output_dir}}}"
        )

        return [
            self._get_package_command(),
            textwrap.dedent(
                f"""\
                    pushd target/package
                    for package in *.crate; do
                        tar xf "$package"
                        rm "$package"
                    done
                    for package in */; do
                        echo '{{"files":{{}}}}' > "$package/.cargo-checksum.json"
                    done
                    cp --recursive --archive --link --no-dereference . {write_registry_bash}
                    popd
                """
            ),
        ]
