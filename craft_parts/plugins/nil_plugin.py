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

"""The nil plugin.

Using this, parts can be defined purely by utilizing properties that are
automatically included, e.g. stage-packages.
"""

from typing import Any, Dict, List, Set

from overrides import override

from .base import Plugin
from .properties import PluginProperties


class NilPluginProperties(PluginProperties):
    """The part properties used by the nil plugin."""

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "NilPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.
        """
        return cls()


class NilPlugin(Plugin):
    """A plugin that defines no build commands.

    The nil plugin is useful in two contexts:

    First, it can be used for parts that identify no source, and can
    be defined purely by using built-in part properties such as
    ``stage-packages``.

    The second use is for parts that do define a source (which will be
    fetched), but for which the build step then needs to be explicitly
    defined using ``override-build``; otherwise, even though the source
    is fetched, nothing will end up in that part's install directory. In
    short, for the case of a part that uses the nil plugin and defines a
    source, it is up to the developer to then define the ``override-build``
    step that, in some way, populates the ``$CRAFT_PART_INSTALL`` directory.
    """

    properties_class = NilPluginProperties

    supports_strict_mode = True

    @override
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_pull_commands(self) -> List[str]:
        """Return a list commands to retrieve dependencies during the pull step."""
        return []

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        return []
