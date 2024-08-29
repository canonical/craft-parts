# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2024 Canonical Ltd.
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
from typing import Literal, cast

from overrides import override

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class DotnetPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Dotnet plugin."""

    plugin: Literal["dotnet"] = "dotnet"

    dotnet_build_configuration: str = "Release"
    dotnet_self_contained_runtime_identifier: str | None = None

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class DotPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Dotnet plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
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

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

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
