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

from craft_parts.plugins import Plugin, PluginProperties


class StrictTestPlugin(Plugin):
    """Test plugin that is strict (works in offline builds)."""

    properties_class = PluginProperties

    supports_strict_mode = True

    def get_pull_commands(self) -> list[str]:
        return [f"strict mode: {self._part_info.strict_mode}"]

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []


class NonStrictTestPlugin(Plugin):
    """Test plugin that is *not* strict (does *not* work in offline builds)."""

    properties_class = PluginProperties

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []
