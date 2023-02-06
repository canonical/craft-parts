# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
"""Plugins used in unit tests."""
from typing import Dict, List, Set

from craft_parts.plugins import Plugin, PluginProperties, StrictPlugin


class StrictTestPlugin(StrictPlugin):
    """Test plugin that is strict (works in offline builds)."""

    properties_class = PluginProperties

    def get_pull_prepare_commands(self) -> List[str]:
        return ["echo StrictTestPlugin.get_pull_prepare_commands()"]

    def get_build_snaps(self) -> Set[str]:
        return set()

    def get_build_packages(self) -> Set[str]:
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        return {}

    def get_build_commands(self) -> List[str]:
        return []


class NonStrictTestPlugin(Plugin):
    """Test plugin that is *not* strict (does *not* work in offline builds)."""

    properties_class = PluginProperties

    def get_build_snaps(self) -> Set[str]:
        return set()

    def get_build_packages(self) -> Set[str]:
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        return {}

    def get_build_commands(self) -> List[str]:
        return []
