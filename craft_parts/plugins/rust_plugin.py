# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""The rust plugin."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, cast

from pydantic import conlist

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)

# A workaround for mypy false positives
# see https://github.com/samuelcolvin/pydantic/issues/975#issuecomment-551147305
if TYPE_CHECKING:
    UniqueStrList = List[str]
else:
    UniqueStrList = conlist(str, unique_items=True)


class RustPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the rust plugin."""

    # part properties required by the plugin
    rust_features: UniqueStrList = []
    rust_path: UniqueStrList = ["."]
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "RustPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="rust", required=["source"]
        )
        return cls(**plugin_data)


class RustPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Rust plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment has the dependencies to build Rust applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        for dependency in ["cargo", "rustc"]:
            self.validate_dependency(
                dependency=dependency,
                plugin_name="rust",
                part_dependencies=part_dependencies,
            )


class RustPlugin(Plugin):
    """A plugin for rust projects.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:
        - rust-features
          (list of unique strings; default: [])
          List of rust features to install.
        - rust-path
          (list of unique strings; default: ["."])
          Path of rust project. Currently, only the first path in the list is used.
    """

    properties_class = RustPluginProperties
    validator_class = RustPluginEnvironmentValidator

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"gcc", "git"}

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {"PATH": "${HOME}/.cargo/bin:${PATH}"}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(RustPluginProperties, self._options)

        install_command_list = [
            "cargo",
            "install",
            "--locked",
            "--path",
            options.rust_path[0],  # TODO: support more than 1 path
            "--root",
            '"${CRAFT_PART_INSTALL}"',
            "--force",
        ]

        if options.rust_features:
            install_command_list.extend(
                ["--features", f"'{' '.join(options.rust_features)}'"]
            )

        return [" ".join(install_command_list)]
