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


@pytest.fixture(params=["default", "partitions"], autouse=True)
def partitions(request: pytest.FixtureRequest) -> list[str]:
    if request.param == "partitions":
        return ["default", "mypart", "yourpart"]
    return ["default"]
