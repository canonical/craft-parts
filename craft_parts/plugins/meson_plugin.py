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

"""The Meson plugin."""


import logging
import shlex
from typing import Any, Dict, List, Optional, Set, cast

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class MesonPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the Go plugin."""

    meson_parameters: List[str] = []

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
            data, plugin_name="meson", required=["source"]
        )
        return cls(**plugin_data)


class MesonPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Meson plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If the environment is invalid.
        """
        for dependency in ["meson", "ninja"]:
            self.validate_dependency(
                dependency=dependency,
                plugin_name="meson",
                part_dependencies=part_dependencies,
            )


class MesonPlugin(Plugin):
    """A plugin for meson projects.

    The meson plugin requires meson installed on your system. This can
    be achieved by adding the appropriate meson package to ``build-packages``
    or ``build-snaps``, or to have it installed or built in a different part.
    In this case, the name of the part supplying meson must be "meson".

    The meson plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    - ``meson-parameters``
      (list of strings)
      List of parameters used to configure the meson based project.
    """

    properties_class = MesonPluginProperties
    validator_class = MesonPluginEnvironmentValidator

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True

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
        options = cast(MesonPluginProperties, self._options)

        meson_cmd = ["meson", str(self._part_info.part_src_subdir)]
        if options.meson_parameters:
            meson_cmd.extend(shlex.quote(p) for p in options.meson_parameters)

        return [
            " ".join(meson_cmd),
            "ninja",
            f"DESTDIR={self._part_info.part_install_dir} ninja install",
        ]
