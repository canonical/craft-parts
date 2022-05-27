# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.executor.collisions import check_for_stage_collisions
from craft_parts.parts import Part


@pytest.fixture
def part0(tmpdir) -> Part:
    part = Part("part0", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    p.mkdir(parents=True)
    (p / "file.pc").write_text(f"prefix={part.part_install_dir}\nName: File")
    return part


@pytest.fixture
def part1(tmpdir) -> Part:
    part = Part("part1", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "a" / "1").write_text("")
    (p / "file.pc").write_text(f"prefix={part.part_install_dir}\nName: File")
    return part


@pytest.fixture
def part2(tmpdir) -> Part:
    part = Part("part2", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "1").write_text("1")
    (p / "2").write_text("")
    (p / "a" / "2").write_text("a/2")
    (p / "a" / "file.pc").write_text(f"prefix={part.part_install_dir}\nName: File")
    return part


@pytest.fixture
def part3(tmpdir) -> Part:
    part = Part("part3", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "b").mkdir()
    (p / "1").write_text("2")
    (p / "a" / "2").write_text("")
    return part


@pytest.fixture
def part4(tmpdir) -> Part:
    part = Part("part4", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    (p / "a").mkdir(parents=True)
    (p / "a" / "2").write_text("")
    (p / "file.pc").write_text(f"prefix={part.part_install_dir}\nName: ConflictFile")
    return part


@pytest.fixture
def part5(tmpdir) -> Part:
    # Create a new part with a symlink that collides with part1's
    # non-symlink.
    part = Part("part5", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    p.mkdir(parents=True)
    (p / "a").symlink_to("foo")

    return part


@pytest.fixture
def part6(tmpdir) -> Part:
    # Create a new part with a symlink that points to a different place
    # than part5's symlink.
    part = Part("part6", {}, project_dirs=ProjectDirs(work_dir=tmpdir))
    p = part.part_install_dir
    p.mkdir(parents=True)
    (p / "a").symlink_to("bar")

    return part


class TestCollisions:
    """Check collision scenarios."""

    def test_no_collisions(self, part1, part2):
        """No exception is expected as there are no collisions."""
        check_for_stage_collisions([part1, part2])

    def test_no_collisions_between_two_parts_pc_files(self, part0, part1):
        """Pkg-config files have different prefixes (this is ok)."""
        check_for_stage_collisions([part0, part1])

    def test_collisions_between_two_parts(self, part1, part2, part3):
        """Files have different contents."""
        with pytest.raises(errors.PartFilesConflict) as raised:
            check_for_stage_collisions([part1, part2, part3])

        assert raised.value.other_part_name == "part2"
        assert raised.value.part_name == "part3"
        assert sorted(raised.value.conflicting_files) == ["1", "a/2"]

    def test_collisions_checks_symlinks(self, part5, part6):
        """Symlinks point to different targets."""
        with pytest.raises(errors.PartFilesConflict) as raised:
            check_for_stage_collisions([part5, part6])

        assert raised.value.other_part_name == "part5"
        assert raised.value.part_name == "part6"
        assert raised.value.conflicting_files == ["a"]

    def test_collisions_not_both_symlinks(self, part1, part5):
        """Same name for directory and symlink."""
        with pytest.raises(errors.PartFilesConflict) as raised:
            check_for_stage_collisions([part1, part5])

        assert raised.value.other_part_name == "part1"
        assert raised.value.part_name == "part5"
        assert raised.value.conflicting_files == ["a"]

    def test_collisions_between_two_parts_pc_files(self, part1, part4):
        """Pkg-config files have different entries that are not prefix."""
        with pytest.raises(errors.PartFilesConflict) as raised:
            check_for_stage_collisions([part1, part4])

        assert raised.value.other_part_name == "part1"
        assert raised.value.part_name == "part4"
        assert raised.value.conflicting_files == ["file.pc"]

    def test_collision_with_part_not_built(self, tmpdir):
        part_built = Part(
            "part_built",
            {"stage": ["collision"]},
            project_dirs=ProjectDirs(work_dir=tmpdir),
        )

        # a part built has the stage file in the installdir.
        part_built.part_install_dir.mkdir(parents=True)
        (part_built.part_install_dir / "collision").write_text("")

        part_not_built = Part(
            "part_not_built",
            {"stage": ["collision"]},
            project_dirs=ProjectDirs(work_dir=tmpdir),
        )

        # a part not built doesn't have the stage file in the installdir.
        check_for_stage_collisions([part_built, part_not_built])
