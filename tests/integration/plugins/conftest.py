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
"""Configuration for plugins integration tests."""

import pytest
from craft_parts.features import Features


@pytest.fixture(params=["none", "partitions"], autouse=True)
def enabled_features(request: pytest.FixtureRequest):
    Features.reset()
    enable_overlay = "overlay" in request.param
    enable_partitions = "partitions" in request.param
    return Features(
        enable_overlay=enable_overlay,
        enable_partitions=enable_partitions,
    )


@pytest.fixture(autouse=True)
def partitions(enabled_features: Features) -> list[str] | None:
    return (
        ["default", "mypart", "yourpart"]
        if enabled_features.enable_partitions
        else None
    )
