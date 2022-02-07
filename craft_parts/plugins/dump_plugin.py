# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020 Canonical Ltd.
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

"""The dump plugin.

This plugin just dumps the content from a specified part source.
"""

from typing import Any, Dict, List, Set

from .base import Plugin
from .properties import PluginProperties


class DumpPluginProperties(PluginProperties):
    """The part properties used by the dump plugin."""

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate dump properties from the part specification.

        'source' is a required part property.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise ValueError: If a required property is not found.
        """
        if "source" not in data:
            raise ValueError("'source' is required by the dump plugin")
        return cls()


class DumpPlugin(Plugin):
    """Copy the content from the part source."""

    properties_class = DumpPluginProperties

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
        install_dir = self._part_info.part_install_dir
        return [f'cp --archive --link --no-dereference . "{install_dir}"']
