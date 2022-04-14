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

"""The conda plugin."""

import logging
from typing import Any, Dict, List, Optional, Set, cast

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class CondaPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the conda plugin."""

    # part properties required by the plugin
    conda_packages: Optional[List[str]] = None
    conda_python_version: Optional[str] = None
    conda_install_prefix: str = "/snap/${CRAFT_PROJECT_NAME}/current"

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "CondaPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data,
            plugin_name="conda",
        )
        return cls(**plugin_data)


class CondaPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Conda plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment has the dependencies to build Conda applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        self.validate_dependency(
            dependency="conda", part_dependencies=part_dependencies
        )


class CondaPlugin(Plugin):
    """A plugin for conda projects.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:
        - conda-packages
          (list of packages, default: None)
          List of packages for conda to install.
        - conda-python-version
          (str, default: None)
          Python version for conda to use (i.e. "3.9")
        - conda-install-prefix
          (str, default: "/snap/${CRAFT_PROJECT_NAME}/current"
          Directory prefix of where the conda environment will be installed.
    """

    properties_class = CondaPluginProperties
    validator_class = CondaPluginEnvironmentValidator

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
        options = cast(CondaPluginProperties, self._options)

        deploy_command = [
            f"CONDA_TARGET_PREFIX_OVERRIDE={options.conda_install_prefix}",
            "conda",
            "create",
            "--prefix",
            "$CRAFT_PART_INSTALL",
            "--yes",
        ]
        if options.conda_python_version:
            deploy_command.append(f"python={options.conda_python_version}")

        if options.conda_packages:
            deploy_command.extend(options.conda_packages)

        return [" ".join(deploy_command)]
