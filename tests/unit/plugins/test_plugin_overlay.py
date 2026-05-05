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
"""Unit tests for plugin overlay API (CRAFT-5027)."""

from typing import Literal

from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin, PluginProperties


class MinimalOverlayProperties(PluginProperties, frozen=True):
    """Properties for a minimal overlay plugin."""

    plugin: Literal["overlay-test"] = "overlay-test"


class MinimalOverlayPlugin(Plugin):
    """A plugin with uses_overlay=True and all overlay methods implemented."""

    properties_class = MinimalOverlayProperties
    uses_overlay = True

    def get_overlay_packages(self) -> set[str]:
        return {"pkg-a", "pkg-b"}

    def get_overlay_environment(self) -> dict[str, str]:
        return {"OVERLAY_VAR": "overlay_value"}

    def get_overlay_host_commands(self) -> list[str]:
        return ["echo host-command"]

    def get_overlay_chroot_commands(self) -> list[str]:
        return ["echo chroot-command"]

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []


class NoOverlayPlugin(Plugin):
    """A plugin that does NOT use overlay."""

    properties_class = MinimalOverlayProperties
    uses_overlay = False

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return []


class TestPluginOverlayClassVar:
    """Test the uses_overlay class variable."""

    def test_default_uses_overlay_is_false(self):
        assert NoOverlayPlugin.uses_overlay is False

    def test_uses_overlay_true(self):
        assert MinimalOverlayPlugin.uses_overlay is True


class TestPluginOverlayDefaults:
    """Test default return values of overlay methods on base Plugin."""

    def test_default_get_overlay_packages(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = NoOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_packages() == set()

    def test_default_get_overlay_environment(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = NoOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_environment() == {}

    def test_default_get_overlay_host_commands(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = NoOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_host_commands() == []

    def test_default_get_overlay_chroot_commands(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = NoOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_chroot_commands() == []


class TestPluginOverlayImplementation:
    """Test a plugin that implements overlay methods."""

    def test_get_overlay_packages(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = MinimalOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_packages() == {"pkg-a", "pkg-b"}

    def test_get_overlay_environment(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = MinimalOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_environment() == {"OVERLAY_VAR": "overlay_value"}

    def test_get_overlay_host_commands(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = MinimalOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_host_commands() == ["echo host-command"]

    def test_get_overlay_chroot_commands(self, new_dir):
        part = Part("p1", {})
        info = PartInfo(
            project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
            part=part,
        )
        props = MinimalOverlayProperties.unmarshal({})
        plugin = MinimalOverlayPlugin(properties=props, part_info=info)

        assert plugin.get_overlay_chroot_commands() == ["echo chroot-command"]
