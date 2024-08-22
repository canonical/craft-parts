# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

"""Unit tests for the lifecycle manager."""

import sys
from typing import Any

import craft_parts
import pytest
from craft_parts import errors
from craft_parts.lifecycle_manager import LifecycleManager

from tests.unit import test_lifecycle_manager
from tests.unit.common_plugins import NonStrictTestPlugin, StrictTestPlugin


@pytest.fixture
def mock_available_plugins(monkeypatch):
    available = {"strict": StrictTestPlugin, "nonstrict": NonStrictTestPlugin}
    monkeypatch.setattr(craft_parts.plugins.plugins, "_PLUGINS", available)


class TestLifecycleManager(test_lifecycle_manager.TestLifecycleManager):
    """Verify lifecycle manager initialization."""


class TestOverlaySupport:
    """Overlays only supported in linux and must run as root."""

    @pytest.fixture
    def parts_data(self) -> dict[str, Any]:
        return {"parts": {"foo": {"plugin": "nil", "overlay-script": "ls"}}}

    def test_overlay_supported(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "linux")
        mocker.patch("os.geteuid", return_value=0)
        LifecycleManager(
            parts_data,
            application_name="test",
            cache_dir=new_dir,
            base_layer_dir=new_dir,
            base_layer_hash=b"hash",
        )

    def test_overlay_platform_unsupported(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "darwin")
        mocker.patch("os.geteuid", return_value=0)
        with pytest.raises(errors.OverlayPlatformError):
            LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                base_layer_dir=new_dir,
                base_layer_hash=b"hash",
            )

    def test_overlay_requires_root(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "linux")
        mocker.patch("os.geteuid", return_value=1000)
        with pytest.raises(errors.OverlayPermissionError):
            LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                base_layer_dir=new_dir,
                base_layer_hash=b"hash",
            )


class TestPluginProperties(test_lifecycle_manager.TestPluginProperties):
    """Verify if plugin properties are correctly handled."""
