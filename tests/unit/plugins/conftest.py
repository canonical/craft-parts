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

"""Common fixtures for plugin unit tests."""

from pathlib import Path
from typing import Any

import pytest
from craft_parts import Part, PartInfo, ProjectInfo


@pytest.fixture
def part_properties() -> dict[str, Any]:
    return {}


@pytest.fixture
def set_self_contained(part_properties) -> None:
    part_properties["build-attributes"] = ["self-contained"]


@pytest.fixture
def part_info(new_dir: Path, part_properties) -> PartInfo:
    cache_dir = new_dir / "cache"
    cache_dir.mkdir()
    return PartInfo(
        project_info=ProjectInfo(
            application_name="testcraft",
            cache_dir=cache_dir,
        ),
        part=Part("my-part", part_properties),
    )


@pytest.fixture
def maven_settings_path(part_info):
    """The location of the temporary settings file for Maven projects during build."""
    return part_info.part_build_subdir / ".parts/.m2/settings.xml"
