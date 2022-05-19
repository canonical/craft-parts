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

"""The npm plugin."""

import logging
import os
import platform
from textwrap import dedent
from typing import Any, Dict, List, Optional, Set, cast

from pydantic import root_validator

from craft_parts.errors import InvalidArchitecture

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)

_NODE_ARCH_FROM_SNAP_ARCH = {
    "i386": "x86",
    "amd64": "x64",
    "armhf": "armv7l",
    "arm64": "arm64",
    "ppc64el": "ppc64le",
    "s390x": "s390x",
}
_NODE_ARCH_FROM_PLATFORM = {"x86_64": {"32bit": "x86", "64bit": "x64"}}


class NpmPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the npm plugin."""

    # part properties required by the plugin
    npm_include_node: bool = False
    npm_node_version: Optional[str]
    source: str

    @root_validator
    @classmethod
    def node_version_defined(cls, values):
        """If npm-include-node is true, then npm-node-version must be defined."""
        if values.get("npm_include_node") and not values.get("npm_node_version"):
            raise ValueError("npm-node-version is required if npm-include-node is true")
        return values

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "NpmPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="npm", required=["source"]
        )
        return cls(**plugin_data)


class NpmPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the npm plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment has the dependencies to build npm applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        options = cast(NpmPluginProperties, self._options)
        if options.npm_include_node:
            return

        for dependency in ["node", "npm"]:
            self.validate_dependency(
                dependency=dependency,
                plugin_name="npm",
                part_dependencies=part_dependencies,
            )


class NpmPlugin(Plugin):
    """A plugin for npm projects.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:
        - npm-include-node
          (bool; default: False)
          If true, download and include the node binary and its dependencies.
          If npm-include-node is true, then npm-node-version must be defined.

        - npm-node-version
          (str: default: None)
          Which version of node to download (e.g. "16.14.2")
    """

    properties_class = NpmPluginProperties
    validator_class = NpmPluginEnvironmentValidator

    @staticmethod
    def _get_architecture() -> str:
        """Get system architecture, formatted for downloading node.

        :raise InvalidArchitecture: If the system architecture
        isn't compatible with node.
        """
        snap_arch = os.getenv("SNAP_ARCH")
        if snap_arch is not None:
            try:
                node_arch = _NODE_ARCH_FROM_SNAP_ARCH[snap_arch]
            except KeyError as error:
                raise InvalidArchitecture(arch_name=snap_arch) from error
        else:
            machine_type = platform.machine()
            architecture_type = platform.architecture()
            try:
                node_arch = _NODE_ARCH_FROM_PLATFORM[machine_type][architecture_type[0]]
            except KeyError as error:
                raise InvalidArchitecture(
                    arch_name=f"{machine_type} {architecture_type}"
                ) from error

        return node_arch

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        if cast(NpmPluginProperties, self._options).npm_include_node:
            return {"curl", "gcc"}
        return {"gcc"}

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        if cast(NpmPluginProperties, self._options).npm_include_node:
            return dict(PATH="${CRAFT_PART_INSTALL}/bin:${PATH}")
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(NpmPluginProperties, self._options)

        command: List[str] = []

        if options.npm_include_node:
            arch = self._get_architecture()
            version = options.npm_node_version

            node_uri = (
                f"https://nodejs.org/dist/v{version}"
                f"/node-v{version}-linux-{arch}.tar.gz"
            )
            command.append(
                dedent(
                    f"""\
                    if [ ! -f "${{CRAFT_PART_INSTALL}}/bin/node" ]; then
                        curl -s "{node_uri}" |
                        tar xzf - -C "${{CRAFT_PART_INSTALL}}/" \
                        --no-same-owner --strip-components=1
                    fi
                    """
                )
            )
        command.append("npm config set unsafe-perm true")
        command.append(
            'npm install -g --prefix "${CRAFT_PART_INSTALL}" $(npm pack . | tail -1)'
        )
        return command
