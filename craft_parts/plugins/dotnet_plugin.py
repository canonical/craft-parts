# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""The Dotnet plugin."""

import logging
from typing import Any, Dict, List, Optional, Set, cast

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class DotnetPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the Go plugin."""

    dotnet_build_configuration: str = "Release"
    dotnet_self_contained_runtime_identifier: Optional[str]

    # part properties required by the plugin
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate make properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="dotnet", required=["source"]
        )
        return cls(**plugin_data)


class DotPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Dotnet plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.
        """
        self.validate_dependency(
            dependency="dotnet",
            plugin_name="dotnet",
            part_dependencies=part_dependencies,
        )


class DotnetPlugin(Plugin):
    """A plugin for dotnet projects.

    The dotnet plugin requires dotnet installed on your system. This can
    be achieved by adding the appropriate dotnet snap package to ``build-snaps``,
    or to have it installed or built in a different part. In this case, the
    name of the part supplying the dotnet compiler must be "dotnet".

    The dotnet plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    - ``dotnet-build-configuration``
      (string)
      The dotnet build configuration to use. The default is "Release".

    - ``dotnet-self-contained-runtime-identifier``
      (string)
      Create a self contained dotnet application using the specified RuntimeIdentifier.
    """

    properties_class = DotnetPluginProperties
    validator_class = DotPluginEnvironmentValidator

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(DotnetPluginProperties, self._options)

        build_cmd = f"dotnet build -c {options.dotnet_build_configuration}"
        publish_cmd = (
            "dotnet publish "
            f"-c {options.dotnet_build_configuration} "
            f"-o {self._part_info.part_install_dir}"
        )
        if options.dotnet_self_contained_runtime_identifier:
            publish_cmd += (
                " --self-contained "
                f"-r {options.dotnet_self_contained_runtime_identifier}"
            )

        return [build_cmd, publish_cmd]
