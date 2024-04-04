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
import pytest_check  # type: ignore[import]
from craft_parts import ProjectDirs
from craft_parts.utils.partition_utils import get_partition_dir_map


@pytest.mark.parametrize("work_dir", [".", "my_work_dir"])
def test_dirs_partitions(new_dir, work_dir, partitions):
    dirs = ProjectDirs(work_dir=work_dir, partitions=partitions)
    pytest_check.equal(dirs.project_dir, new_dir)
    pytest_check.equal(dirs.work_dir, dirs.work_dir)
    pytest_check.equal(dirs.parts_dir, dirs.work_dir / "parts")
    pytest_check.equal(dirs.overlay_dir, dirs.work_dir / "overlay")
    pytest_check.equal(dirs.overlay_mount_dir, dirs.overlay_dir / "overlay")
    pytest_check.equal(dirs.overlay_packages_dir, dirs.overlay_dir / "packages")
    pytest_check.equal(dirs.overlay_work_dir, dirs.overlay_dir / "work")
    pytest_check.equal(dirs.stage_dir, dirs.work_dir / "stage")
    pytest_check.equal(dirs.prime_dir, dirs.work_dir / "prime")
    pytest_check.equal(dirs.stage_dirs.keys(), set(partitions))
    pytest_check.equal(dirs.prime_dirs.keys(), set(partitions))
    pytest_check.equal(dirs.partition_dir, dirs.work_dir / "partitions")
    pytest_check.equal(
        dirs.stage_dirs,
        get_partition_dir_map(
            base_dir=dirs.work_dir, partitions=partitions, suffix="stage"
        ),
    )
    pytest_check.equal(
        dirs.prime_dirs,
        get_partition_dir_map(
            base_dir=dirs.work_dir, partitions=partitions, suffix="prime"
        ),
    )
