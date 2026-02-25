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
import re
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml
from craft_parts import LifecycleManager, Step
from craft_parts.errors import OverlayStageConflict, PartFilesConflict

# Different cases of part declarations that must result in a conflict between files/dirs
# being staged from the regular build, and from the overlay.
OVERLAY_MUST_COLLIDE_SCENARIOS = {
    "simple": {
        # Part A has a file in its install dir, part B overlays the same file
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              """),
        "regular_part": "A",
        "overlay_part": "B",
    },
    "simple after": {
        # Part A has a file in its install dir, part B overlays the same file; part A
        # comes explicitly *after* B.
        "yaml": textwrap.dedent("""
            parts:
              A:
                after: [B]
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              """),
        "regular_part": "A",
        "overlay_part": "B",
    },
    "two overlay parts": {
        # Part A has a file in its install dir, part B overlays the same file, but
        # part C comes *after* B and also overlays the file (hiding the one in B)
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  echo "from part C" >> $CRAFT_OVERLAY/conflict.txt
              """),
        "regular_part": "A",
        "overlay_part": "C",
    },
    "three overlay parts": {
        # Similar to "two overlay parts", but the part D that overwrites the conflicting
        # file is "further away" from part B on the overlay stack
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  echo "from part C" >> $CRAFT_OVERLAY/not-a-conflict.txt
              D:
                after: [C]
                plugin: nil
                overlay-script: |
                  echo "from part D" >> $CRAFT_OVERLAY/conflict.txt
              """),
        "regular_part": "A",
        "overlay_part": "D",
    },
    "same part": {
        # Part A has a file in its install dir, and overlays the same file
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from BUILD" >> $CRAFT_PART_INSTALL/conflict.txt
                overlay-script: |
                  echo "from OVERLAY" >> $CRAFT_OVERLAY/conflict.txt
              """),
        "regular_part": "A",
        "overlay_part": "A",
    },
    "file and directory": {
        # Part A has a file in its install dir, and overlays the same name as a directory
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from BUILD" >> $CRAFT_PART_INSTALL/conflict
                overlay-script: |
                  mkdir $CRAFT_OVERLAY/conflict
              """),
        "regular_part": "A",
        "overlay_part": "A",
    },
}


# Cases where the overlay and install dirs create items with the same name, but that
# must *not* result in a collision
OVERLAY_MUST_NOT_COLLIDE_SCENARIOS = {
    "simple": {
        # Part A has a file in its install dir, part B overlays the same file with the
        # same contents
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "this is conflict.txt" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "this is conflict.txt" >> $CRAFT_OVERLAY/conflict.txt
              """),
    },
    "layer-hides-file": {
        # Part A has a file in its install dir, part B overlays the same file with
        # different contents but part C removes the file from the overlay.
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "this is from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "this is from part B" >> $CRAFT_OVERLAY/conflict.txt
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm $CRAFT_OVERLAY/conflict.txt
              """),
    },
    "layer-hides-dir": {
        # Part A has a file in its install dir, part B overlays the same name as a dir,
        # but part C removes the dir from the overlay.
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "this is from part A" >> $CRAFT_PART_INSTALL/conflict
              B:
                plugin: nil
                overlay-script: |
                  mkdir $CRAFT_OVERLAY/conflict
              C:
                after: [B]
                plugin: nil
                overlay-script: |
                  rm -r $CRAFT_OVERLAY/conflict
              """),
    },
    "filtered in stage": {
        # Part A has a file in its install dir, part B overlays the same file; part A
        # filters the file through a "stage" declaration
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
                stage:
                  - "-conflict.txt"
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
              """),
    },
    "filtered in overlay": {
        # Part A has a file in its install dir, part B overlays the same file; part B
        # filters the file through an "overlay" declaration
        "yaml": textwrap.dedent("""
            parts:
              A:
                plugin: nil
                override-build: |
                  echo "from part A" >> $CRAFT_PART_INSTALL/conflict.txt
              B:
                plugin: nil
                overlay-script: |
                  echo "from part B" >> $CRAFT_OVERLAY/conflict.txt
                overlay:
                  - "-conflict.txt"
              """),
    },
}


class TestCollisions:
    """Test collision scenarios."""

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

    def test_same_file_contents(self, new_dir, partitions, stub_parts_yaml):
        """Two parts can stage an identical file."""

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

        assert Path(new_dir / "stage/file").read_text() == "same contents"

    def test_different_file_contents(self, new_dir, partitions, stub_parts_yaml):
        """Two parts cannot stage a file with the different contents."""
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

        if partitions:
            assert str(raised.value) == (
                "Failed to stage: parts list the same file with different contents or permissions.\n"
                "Parts 'part2' and 'part1' list the following files for the 'default' partition, but with different contents or permissions:\n"
                "    file"
            )
        else:
            assert str(raised.value) == (
                "Failed to stage: parts list the same file with different contents or permissions.\n"
                "Parts 'part2' and 'part1' list the following files, but with different contents or permissions:\n"
                "    file"
            )

    @staticmethod
    def _run_lifecycle(parts_yaml, new_dir, partitions):
        """Create and run a lifecycle with overlay and optionally partitions."""
        base_dir = Path("base")
        base_dir.mkdir()

        parts = yaml.safe_load(parts_yaml)
        lf = LifecycleManager(
            parts,
            application_name="test_lifecycle",
            cache_dir=new_dir,
            base_layer_dir=base_dir,
            base_layer_hash=b"hash",
            partitions=partitions,
        )

        actions = lf.plan(Step.PRIME)
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    @pytest.mark.parametrize("scenario", list(OVERLAY_MUST_COLLIDE_SCENARIOS.keys()))
    def test_overlay_must_collide(self, new_dir, partitions, scenario):
        data = OVERLAY_MUST_COLLIDE_SCENARIOS[scenario]
        parts_yaml = data["yaml"]
        regular_part = data["regular_part"]
        overlay_part = data["overlay_part"]

        partition_message = ""
        if partitions:
            partition_message = " for the 'default' partition"

        expected_message = re.escape(
            f"Part {regular_part!r} and the overlay of part {overlay_part!r} "
            f"list the following files{partition_message}, "
            "but with different contents or permissions:"
        )

        with pytest.raises(OverlayStageConflict, match=expected_message):
            self._run_lifecycle(parts_yaml, new_dir, partitions)

    @pytest.mark.usefixtures(
        "mock_overlay_support_prerequisites", "add_overlay_feature"
    )
    @pytest.mark.parametrize(
        "scenario", list(OVERLAY_MUST_NOT_COLLIDE_SCENARIOS.keys())
    )
    def test_overlay_must_not_collide(self, new_dir, partitions, scenario):
        data = OVERLAY_MUST_NOT_COLLIDE_SCENARIOS[scenario]
        parts_yaml = data["yaml"]

        self._run_lifecycle(parts_yaml, new_dir, partitions)
