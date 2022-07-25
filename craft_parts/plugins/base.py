# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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

import abc
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type

from pydantic import BaseModel

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

    properties_class: Type[PluginProperties]
    validator_class = PluginEnvironmentValidator

    def __init__(
        self, *, properties: PluginProperties, part_info: "infos.PartInfo"
    ) -> None:
        self._options = properties
        self._part_info = part_info

    @abc.abstractmethod
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""

    @abc.abstractmethod
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""

    @abc.abstractmethod
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return False

    @abc.abstractmethod
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""


class PluginModel(BaseModel):
    """Model for plugins using pydantic validation.

    Plugins with configuration properties can use pydantic validation to unmarshal
    data from part specs. In this case, extract plugin-specific properties using
    the :func:`extract_plugin_properties` helper.
    """

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "forbid"
        allow_mutation = False
        alias_generator = lambda s: s.replace("_", "-")  # noqa: E731


def extract_plugin_properties(
    data: Dict[str, Any], *, plugin_name: str, required: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Obtain plugin-specifc entries from part properties.

    :param data: A dictionary containing all part properties.
    :plugin_name: The name of the plugin.

    :return: A dictionary with plugin properties.
    """
    if required is None:
        required = []

    plugin_data: Dict[str, Any] = {}
    prefix = f"{plugin_name}-"

    for key, value in data.items():
        if key.startswith(prefix) or key in required:
            plugin_data[key] = value

    return plugin_data
