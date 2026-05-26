# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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
"""Shared test plugins for overlay integration tests (CRAFT-5027)."""

from craft_parts.plugins import Plugin, PluginProperties


class OverlayPluginProperties(PluginProperties, frozen=True):
    """Properties for the test overlay plugins."""


class ChrootCommandPlugin(Plugin):
    """A plugin that runs chroot commands inside the overlay."""

    properties_class = OverlayPluginProperties
    uses_overlay = True

    def get_overlay_chroot_commands(self):
        return ["echo ok > /chroot-proof.txt"]

    def get_build_snaps(self):
        return set()

    def get_build_packages(self):
        return set()

    def get_build_environment(self):
        return {}

    def get_build_commands(self):
        return []


class PackageOverlayPlugin(Plugin):
    """A plugin that installs overlay packages and runs chroot commands."""

    properties_class = OverlayPluginProperties
    uses_overlay = True

    def get_overlay_packages(self):
        return {"hello"}

    def get_overlay_chroot_commands(self):
        return ["hello --greeting 'plugin-overlay-works' > /plugin-overlay-proof.txt"]

    def get_build_snaps(self):
        return set()

    def get_build_packages(self):
        return set()

    def get_build_environment(self):
        return {}

    def get_build_commands(self):
        return []
