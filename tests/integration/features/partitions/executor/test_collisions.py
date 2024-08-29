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

from pathlib import Path
from typing import Any

import pytest
from craft_parts import LifecycleManager, Step
from craft_parts.errors import PartFilesConflict
from tests.integration.executor import test_collisions


class TestCollisions(test_collisions.TestCollisions):
    """Test collision scenarios with partitions enabled."""


class TestCollisionsInPartitions:
    """Test collision scenarios in partition stage dirs."""

    @pytest.fixture
    def stub_parts_yaml(self) -> dict[str, Any]:
        """Return a part dictionary containing 2 parts."""
        return {
            "parts": {
                "part1": {
                    "plugin": "dump",
                    "source": "part1",
                },
                "part2": {
                    "plugin": "dump",
                    "source": "part2",
                },
            }
        }

    def test_same_file_contents_same_partition(
        self, new_dir, partitions, stub_parts_yaml
    ):
        """Two parts can stage an identical file in the same partition."""
        stub_parts_yaml["parts"]["part1"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }
        stub_parts_yaml["parts"]["part2"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }

        Path(new_dir / "part1").mkdir()
        Path(new_dir / "part1/file").write_text("same contents")
        Path(new_dir / "part2").mkdir()
        Path(new_dir / "part2/file").write_text("same contents")

        lcm = LifecycleManager(
            stub_parts_yaml,
            application_name="test",
            cache_dir=Path(),
            partitions=partitions,
        )

        with lcm.action_executor() as aex:
            aex.execute(lcm.plan(Step.STAGE))

        assert (
            Path(new_dir / "partitions/mypart/stage/file").read_text()
            == "same contents"
        )

    def test_same_file_contents_different_partition(
        self, new_dir, partitions, stub_parts_yaml
    ):
        """Two parts can stage an identical file in different partitions."""
        stub_parts_yaml["parts"]["part1"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }

        Path(new_dir / "part1").mkdir()
        Path(new_dir / "part1/file").write_text("contents")
        Path(new_dir / "part2").mkdir()
        Path(new_dir / "part2/file").write_text("contents")

        lcm = LifecycleManager(
            stub_parts_yaml,
            application_name="test",
            cache_dir=Path(),
            partitions=partitions,
        )

        with lcm.action_executor() as aex:
            aex.execute(lcm.plan(Step.STAGE))

        assert Path(new_dir / "stage/file").read_text() == "contents"
        assert Path(new_dir / "partitions/mypart/stage/file").read_text() == "contents"

    def test_different_file_contents_different_partition(
        self, new_dir, partitions, stub_parts_yaml
    ):
        """Two parts can stage a file with different contents in different partitions."""
        stub_parts_yaml["parts"]["part1"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }

        Path(new_dir / "part1").mkdir()
        Path(new_dir / "part1/file").write_text("contents")
        Path(new_dir / "part2").mkdir()
        Path(new_dir / "part2/file").write_text("conflicting contents")

        lcm = LifecycleManager(
            stub_parts_yaml,
            application_name="test",
            cache_dir=Path(),
            partitions=partitions,
        )

        with lcm.action_executor() as aex:
            aex.execute(lcm.plan(Step.STAGE))

        assert Path(new_dir / "stage/file").read_text() == "conflicting contents"
        assert Path(new_dir / "partitions/mypart/stage/file").read_text() == "contents"

    def test_different_file_contents_same_partition(
        self, new_dir, partitions, stub_parts_yaml
    ):
        """Two parts cannot stage a file with the different contents in the same partition."""
        stub_parts_yaml["parts"]["part1"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }
        stub_parts_yaml["parts"]["part2"]["organize"] = {
            "(default)/file": "(mypart)/file"
        }

        Path(new_dir / "part1").mkdir()
        Path(new_dir / "part1/file").write_text("contents")
        Path(new_dir / "part2").mkdir()
        Path(new_dir / "part2/file").write_text("conflicting contents")

        lcm = LifecycleManager(
            stub_parts_yaml,
            application_name="test",
            cache_dir=Path(),
            partitions=partitions,
        )

        with pytest.raises(PartFilesConflict) as raised:
            with lcm.action_executor() as aex:
                aex.execute(lcm.plan(Step.STAGE))

        assert str(raised.value) == (
            "Failed to stage: parts list the same file with different contents or permissions.\n"
            "Parts 'part2' and 'part1' list the following files for the 'mypart' partition, but with different contents or permissions:\n"
            "    file"
        )
