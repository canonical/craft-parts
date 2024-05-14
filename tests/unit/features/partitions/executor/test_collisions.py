# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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
from craft_parts import Part, ProjectDirs, errors
from craft_parts.executor.collisions import check_for_stage_collisions

from tests.unit.executor import test_collisions


class TestCollisions(test_collisions.TestCollisions):
    """Check collision scenarios with partitions enabled."""


class TestCollisionsPartitionError:
    def test_partitions_enabled_but_not_defined(self, partitions, tmpdir):
        """Raise an error if partitions are enabled but not defined."""
        part = Part(
            name="part",
            data={},
            project_dirs=ProjectDirs(work_dir=tmpdir, partitions=partitions),
            partitions=partitions,
        )

        with pytest.raises(errors.FeatureError) as raised:
            check_for_stage_collisions(part_list=[part], partitions=None)

        assert raised.value.brief == (
            "Partitions feature is enabled but no partitions specified."
        )
