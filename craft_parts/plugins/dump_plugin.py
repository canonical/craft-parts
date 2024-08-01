# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020,2024 Canonical Ltd.
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

from typing import Literal

from overrides import override

from .base import Plugin
from .properties import PluginProperties


class DumpPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the dump plugin."""

    plugin: Literal["dump"] = "dump"
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class DumpPlugin(Plugin):
    """Copy the content from the part source."""

    properties_class = DumpPluginProperties

    supports_strict_mode = True

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list commands to retrieve dependencies during the pull step."""
        return []

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
        install_dir = self._part_info.part_install_dir
        return [f'cp --archive --link --no-dereference . "{install_dir}"']
