# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
import pytest
from craft_parts import ProjectDirs, ProjectInfo
from craft_parts.executor import environment


@pytest.mark.parametrize(
    ("partitions", "variables"),
    [
        (["default"], {"CRAFT_DEFAULT_STAGE", "CRAFT_DEFAULT_PRIME"}),
        (
            # exercise lowercase alphabetical, numbers, and hyphens
            ["default", "abc123", "abc-123", "foo1/bar-baz2"],
            {
                "CRAFT_DEFAULT_STAGE",
                "CRAFT_DEFAULT_PRIME",
                "CRAFT_ABC123_STAGE",
                "CRAFT_ABC123_PRIME",
                "CRAFT_ABC_123_STAGE",
                "CRAFT_ABC_123_PRIME",
                "CRAFT_FOO1_BAR_BAZ2_STAGE",
                "CRAFT_FOO1_BAR_BAZ2_PRIME",
            },
        ),
    ],
)
def test_get_global_environment(new_dir, partitions, variables: set):
    """Test that expand_environment behaves correctly with partitions enabled."""
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work", partitions=partitions),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
        partitions=partitions,
    )

    actual = environment._get_global_environment(info)
    assert variables.issubset(actual.keys())
    assert actual["CRAFT_STAGE"] == actual["CRAFT_DEFAULT_STAGE"]
    assert actual["CRAFT_PRIME"] == actual["CRAFT_DEFAULT_PRIME"]
