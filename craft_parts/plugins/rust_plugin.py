# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022-2023 Canonical Ltd.
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

"""The craft Rust plugin."""

import logging
import subprocess
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, cast

from overrides import override
from pydantic import conlist

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

GET_RUSTUP_COMMAND_TEMPLATE = (
    "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | "
    "sh -s -- -y --no-modify-path --profile=minimal --default-toolchain {channel}"
)

logger = logging.getLogger(__name__)

# A workaround for mypy false positives
# see https://github.com/samuelcolvin/pydantic/issues/975#issuecomment-551147305
# The proper fix requires Python 3.9+ (needs `typing.Annotated`)
if TYPE_CHECKING:
    UniqueStrList = List[str]
else:
    UniqueStrList = conlist(str, unique_items=True)


class RustPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the Rust plugin."""

    # part properties required by the plugin
    rust_features: UniqueStrList = []
    rust_path: UniqueStrList = ["."]
    rust_channel: Optional[str] = None
    rust_use_global_lto: bool = False
    rust_no_default_features: bool = False
    source: str
    after: Optional[UniqueStrList] = None

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "RustPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data,
            plugin_name="rust",
            required=["source"],
        )
        return cls(**plugin_data)


class RustPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Rust plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: Optional[List[str]] = None
    ) -> None:
        """Ensure the environment has the dependencies to build Rust applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        if "rust-deps" in (part_dependencies or []):
            options = cast(RustPluginProperties, self._options)
            if options.rust_channel and options.rust_channel != "none":
                raise validator.errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="rust-deps can not be used"
                    "when rust-channel is also specified",
                )
            for dependency in ["cargo", "rustc"]:
                self.validate_dependency(
                    dependency=dependency,
                    plugin_name="rust",
                    part_dependencies=part_dependencies,
                )


class RustPlugin(Plugin):
    """A craft plugin for Rust applications.

    This Rust plugin is useful for building Rust based parts.

    Rust uses cargo to drive the build.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:
        - rust-channel
          (string, default "stable")
          Used to select which Rust channel or version to use.
          It can be one of "stable", "beta", "nightly" or a version number.
          If you don't want this plugin to install Rust toolchain for you,
          you can put "none" for this option.

        - rust-features
          (list of strings)
          Features used to build optional dependencies

        - rust-path
          (list of strings, default [.])
          Build specific crates inside the workspace

        - rust-no-default-features
          (boolean, default False)
          Whether to disable the default features in this crate.
          Equivalent to setting `--no-default-features` on the commandline.

        - rust-use-global-lto
          (boolean, default False)
          Whether to use global LTO.
          This option may significantly impact the build performance but
          reducing the final binary size.
          This will forcibly enable LTO for all the crates you specified,
          regardless of whether you have LTO enabled in the Cargo.toml file
    """

    properties_class = RustPluginProperties
    validator_class = RustPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"curl", "gcc", "git", "pkg-config", "findutils"}

    def _check_system_rust(self) -> bool:
        """Check if Rust is installed on the system."""
        try:
            rust_version = subprocess.check_output(["rustc", "--version"], text=True)
            cargo_version = subprocess.check_output(["cargo", "--version"], text=True)
            return "rustc" in rust_version and "cargo" in cargo_version
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_rustup(self) -> bool:
        try:
            rustup_version = subprocess.check_output(["rustup", "--version"])
            return "rustup" in rustup_version.decode("utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_setup_rustup(self, channel: str) -> List[str]:
        return [GET_RUSTUP_COMMAND_TEMPLATE.format(channel=channel)]

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            "PATH": "${HOME}/.cargo/bin:${PATH}",
        }

    @override
    def get_pull_commands(self) -> List[str]:
        """Return a list of commands to run during the pull step."""
        options = cast(RustPluginProperties, self._options)
        if not options.rust_channel and self._check_system_rust():
            logger.info("Rust is installed on the system, skipping rustup")
            return []

        rust_channel = options.rust_channel or "stable"
        if rust_channel == "none":
            return []
        if not self._check_rustup():
            logger.info("Rustup not found, installing it")
            return self._get_setup_rustup(rust_channel)
        logger.info("Switch rustup channel to %s", rust_channel)
        return [
            f"rustup update {rust_channel}",
            f"rustup default {rust_channel}",
        ]

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(RustPluginProperties, self._options)

        rust_build_cmd: List[str] = []
        config_cmd: List[str] = []

        if options.rust_features:
            features_string = " ".join(options.rust_features)
            config_cmd.extend(["--features", f"'{features_string}'"])

        if options.rust_use_global_lto:
            logger.info("Adding overrides for LTO support")
            config_cmd.extend(
                [
                    "--config 'profile.release.lto = true'",
                    "--config 'profile.release.codegen-units = 1'",
                ]
            )

        if options.rust_no_default_features:
            config_cmd.append("--no-default-features")

        for crate in options.rust_path:
            logger.info("Generating build commands for %s", crate)
            config_cmd_string = " ".join(config_cmd)
            # pylint: disable=line-too-long
            rust_build_cmd_single = dedent(
                f"""\
                if cargo read-manifest --manifest-path "{crate}"/Cargo.toml > /dev/null; then
                    cargo install -f --locked --path "{crate}" --root "{self._part_info.part_install_dir}" {config_cmd_string}
                    # remove the installation metadata
                    rm -f "{self._part_info.part_install_dir}"/.crates{{.toml,2.json}}
                else
                    # virtual workspace is a bit tricky,
                    # we need to build the whole workspace and then copy the binaries ourselves
                    pushd "{crate}"
                    cargo build --workspace --release {config_cmd_string}
                    # install the final binaries
                    find ./target/release -maxdepth 1 -executable -exec install -Dvm755 {{}} "{self._part_info.part_install_dir}" ';'
                    # remove proc_macro objects
                    for i in "{self._part_info.part_install_dir}"/*.so; do
                        readelf --wide --dyn-syms "$i" | grep -q '__rustc_proc_macro_decls_[0-9a-f]*__' && \
                        rm -fv "$i"
                    done
                    popd
                fi\
                """
            )
            rust_build_cmd.append(rust_build_cmd_single)
        return rust_build_cmd
