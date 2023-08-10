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
import pytest
import pytest_check  # type: ignore[import]

from craft_parts import ProjectDirs


@pytest.mark.parametrize("work_dir", [".", "my_work_dir"])
def test_dirs_partitions(new_dir, work_dir):
    dirs = ProjectDirs(work_dir=work_dir)
    pytest_check.equal(dirs.project_dir, new_dir)
    pytest_check.equal(dirs.work_dir, new_dir / work_dir)
    pytest_check.equal(dirs.parts_dir, new_dir / work_dir / "parts")
    pytest_check.equal(dirs.overlay_dir, new_dir / work_dir / "overlay")
    pytest_check.equal(dirs.overlay_mount_dir, new_dir / work_dir / "overlay/overlay")
    pytest_check.equal(
        dirs.overlay_packages_dir, new_dir / work_dir / "overlay/packages"
    )
    pytest_check.equal(dirs.overlay_work_dir, new_dir / work_dir / "overlay/work")
    pytest_check.equal(dirs.stage_dir, new_dir / work_dir / "stage/default")
    pytest_check.equal(dirs.prime_dir, new_dir / work_dir / "prime/default")
