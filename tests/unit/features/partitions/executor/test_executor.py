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

import os
from collections.abc import Iterable
from pathlib import Path

from craft_parts.executor import Executor
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.steps import Step
from craft_parts.utils.partition_utils import get_partition_dir_map

from tests.unit.executor import test_executor


class TestExecutor:
    """Verify executor class methods with partitions."""

    def _make_files(self, dirs: Iterable[Path], filename: str) -> None:
        """Create a file in a series of directories."""
        for directory in dirs:
            directory.mkdir(parents=True)
            (directory / filename).touch()

    def test_clean(self, new_path, partitions):
        """Clean a project with partitions enabled."""
        p1 = Part("p1", {"plugin": "nil"}, partitions=partitions)
        self._make_files(p1.part_install_dirs.values(), "part1-install-file")

        p2 = Part("p2", {"plugin": "nil"}, partitions=partitions)
        self._make_files(p2.part_install_dirs.values(), "part2-install-file")

        stage_dirs = get_partition_dir_map(
            base_dir=new_path, partitions=partitions, suffix="stage"
        ).values()
        self._make_files(stage_dirs, "staged-file")

        prime_dirs = get_partition_dir_map(
            base_dir=new_path, partitions=partitions, suffix="prime"
        ).values()
        self._make_files(prime_dirs, "primed-file")

        assert all(
            (install_dir / "part1-install-file").exists()
            for install_dir in p1.part_install_dirs.values()
        )
        assert (
            (install_dir / "part2-install-file").exists()
            for install_dir in p2.part_install_dirs.values()
        )
        assert all((stage_dir / "staged-file").exists() for stage_dir in stage_dirs)
        assert all((prime_dir / "primed-file").exists() for prime_dir in prime_dirs)

        info = ProjectInfo(
            application_name="test", cache_dir=new_path, partitions=partitions
        )

        # Create symlinks if default partition aliased
        if info.is_default_partition_aliased:
            info.alias_partition_dir.mkdir(parents=True, exist_ok=True)  # pyright: ignore[reportOptionalMemberAccess]
            os.symlink(
                new_path / "stage",
                info.stage_alias_symlink,  # type: ignore[reportArgumentType]
                target_is_directory=True,
            )
            os.symlink(
                new_path / "prime",
                info.prime_alias_symlink,  # type: ignore[reportArgumentType]
                target_is_directory=True,
            )
            os.symlink(
                new_path / "parts",
                info.parts_alias_symlink,  # type: ignore[reportArgumentType]
                target_is_directory=True,
            )

        e = Executor(project_info=info, part_list=[p1, p2])
        e.clean(Step.PULL)

        assert all(
            (install_dir / "part1-install-file").exists() is False
            for install_dir in p1.part_install_dirs.values()
        )
        assert all(
            (install_dir / "part2-install-file").exists() is False
            for install_dir in p2.part_install_dirs.values()
        )
        assert all(
            (stage_dir / "staged-file").exists() is False for stage_dir in stage_dirs
        )
        assert all(
            (prime_dir / "primed-file").exists() is False for prime_dir in prime_dirs
        )

        # Test symlinks for alias to default partition
        assert (
            info.stage_alias_symlink is None
            or info.stage_alias_symlink.exists() is False
        )
        assert (
            info.prime_alias_symlink is None
            or info.prime_alias_symlink.exists() is False
        )
        assert (
            info.parts_alias_symlink is None
            or info.parts_alias_symlink.exists() is False
        )

    def test_clean_part(self, new_dir, partitions):
        """Clean a part with partitions enabled."""
        p1 = Part("p1", {"plugin": "nil"}, partitions=partitions)
        self._make_files(p1.part_install_dirs.values(), "part1-install-file")

        p2 = Part("p2", {"plugin": "nil"}, partitions=partitions)
        self._make_files(p2.part_install_dirs.values(), "part2-install-file")

        assert all(
            (install_dir / "part1-install-file").exists()
            for install_dir in p1.part_install_dirs.values()
        )
        assert all(
            (install_dir / "part2-install-file").exists()
            for install_dir in p2.part_install_dirs.values()
        )

        info = ProjectInfo(
            application_name="test",
            cache_dir=new_dir,
            partitions=partitions,
        )
        e = Executor(project_info=info, part_list=[p1, p2])
        e.clean(Step.PULL, part_names=["p1"])

        assert all(
            (install_dir / "part1-install-file").exists() is False
            for install_dir in p1.part_install_dirs.values()
        )
        assert all(
            (install_dir / "part2-install-file").exists()
            for install_dir in p2.part_install_dirs.values()
        )

        e.clean(Step.PULL, part_names=["p2"])

        assert (
            (install_dir / "part1-install-file").exists() is False
            for install_dir in p1.part_install_dirs.values()
        )
        assert (
            (install_dir / "part2-install-file").exists() is False
            for install_dir in p2.part_install_dirs.values()
        )


class TestPackages(test_executor.TestPackages):
    """Verify package installation during the execution phase with partitions."""


class TestExecutionContext(test_executor.TestExecutionContext):
    """Verify execution context methods with partitions."""
