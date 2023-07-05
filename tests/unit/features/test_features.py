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

"""Unit tests for the lifecycle manager with multiple features."""

import pytest

from craft_parts import errors
from craft_parts.features import Features
from craft_parts.lifecycle_manager import LifecycleManager


class TestFeaturesSupport:
    """Tests lifecycle manager when multiple features are enabled."""

    def test_partitions_and_overlay(self, new_dir):
        """Raise an error if partitions and overlay features are both enabled."""
        Features.reset()
        Features(enable_overlay=True, enable_partitions=True)

        with pytest.raises(errors.FeatureEnabled) as raised:
            LifecycleManager(
                {"parts": {"foo": {"plugin": "nil"}}},
                application_name="test",
                cache_dir=new_dir,
            )
        assert (
            raised.value.message
            == "Overlay and partitions features are mutually exclusive."
        )

        Features.reset()
