# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2024 Canonical Ltd.
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

"""Plugin base class and definitions."""

from __future__ import annotations

import abc
from collections.abc import Collection
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from craft_parts.actions import ActionProperties

from .properties import PluginProperties
from .validator import PluginEnvironmentValidator

if TYPE_CHECKING:
    # import module to avoid circular imports in sphinx doc generation
    from craft_parts import infos


class Plugin(abc.ABC):
    """The base class for plugins.

    :cvar properties_class: The plugin properties class.
    :cvar validator_class: The plugin environment validator class.

    :param part_info: The part information for the applicable part.
    :param properties: Part-defined properties.
    """

    properties_class: type[PluginProperties]
    validator_class = PluginEnvironmentValidator

    supports_strict_mode = False
    """Plugins that can run in 'strict' mode must set this classvar to True."""

    def __init__(
        self, *, properties: PluginProperties, part_info: infos.PartInfo
    ) -> None:
        self._options = properties
        self._part_info = part_info
        self._action_properties: ActionProperties

    def get_pull_commands(self) -> list[str]:
        """Return the commands to retrieve dependencies during the pull step."""
        return []

    @abc.abstractmethod
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""

    @abc.abstractmethod
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""

    @abc.abstractmethod
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return False

    @abc.abstractmethod
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""

    def set_action_properties(self, action_properties: ActionProperties) -> None:
        """Store a copy of the given action properties.

        :param action_properties: The properties to store.
        """
        self._action_properties = deepcopy(action_properties)


class JavaPlugin(Plugin):
    """A base class for java-related plugins.

    Provide common methods to deal with the java executable location and
    symlink creation.
    """

    def _get_java_post_build_commands(self) -> list[str]:
        """Get the bash commands to structure a Java build in the part's install dir.

        :return: The returned list contains the bash commands to do the following:

          - Create bin/ and jar/ directories in ${CRAFT_PART_INSTALL};
          - Find the ``java`` executable (provided by whatever jre the part used) and
            link it as ${CRAFT_PART_INSTALL}/bin/java;
          - Hardlink the .jar files generated in ${CRAFT_PART_BUILD} to
            ${CRAFT_PART_INSTALL}/jar.
        """
        # pylint: disable=line-too-long
        link_java = [
            '# Find the "java" executable and make a link to it in CRAFT_PART_INSTALL/bin/java',
            "mkdir -p ${CRAFT_PART_INSTALL}/bin",
            "java_bin=$(find ${CRAFT_PART_INSTALL} -name java -type f -executable)",
            "ln -s --relative $java_bin ${CRAFT_PART_INSTALL}/bin/java",
        ]

        link_jars = [
            "# Find all the generated jars and hardlink them inside CRAFT_PART_INSTALL/jar/",
            "mkdir -p ${CRAFT_PART_INSTALL}/jar",
            r'find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \;',
        ]
        # pylint: enable=line-too-long

        return link_java + link_jars


def extract_plugin_properties(
    data: dict[str, Any], *, plugin_name: str, required: Collection[str] | None = None
) -> dict[str, Any]:
    """Obtain plugin-specific entries from part properties.

    Plugin-specific properties must be prefixed with the name of the plugin.

    :param data: A dictionary containing all part properties.
    :plugin_name: The name of the plugin.

    :return: A dictionary with plugin properties.
    """
    if required is None:
        required = []

    plugin_data: dict[str, Any] = {}
    prefix = f"{plugin_name}-"

    for key, value in data.items():
        if key.startswith(prefix) or key in required:
            plugin_data[key] = value

    return plugin_data
