# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Plugin base class and definitions."""

import abc
from typing import Dict, List, Optional, Set, Type

from craft_parts.infos import PartInfo

from .properties import PluginProperties


class Plugin(abc.ABC):
    """The base class for plugins.

    :cvar properties_class: The plugin properties class.

    :param part_name: the name of the part this plugin is instantiated to.
    :param options: an object representing part defined properties.
    """

    properties_class: Type[PluginProperties]

    def __init__(
        self, *, options: Optional[PluginProperties], part_info: PartInfo
    ) -> None:
        if not options:
            options = PluginProperties()

        self._name = part_info.part_name
        self._options = options
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

    @property
    def out_of_source_build(self):
        """Return whether the plugin performs out-of-source-tree builds."""
        return False

    @abc.abstractmethod
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
