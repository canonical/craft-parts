# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2026 Canonical Ltd.
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
from craft_parts import steps
from craft_parts.parts import Part
from craft_parts.steps import Step


@pytest.mark.parametrize(
    ("tc_step", "tc_result"),
    [
        (Step.PULL, None),
        (Step.OVERLAY, None),
        (Step.BUILD, Step.STAGE),
        (Step.STAGE, Step.STAGE),
        (Step.PRIME, Step.PRIME),
    ],
)
def test_prerequisite_step(tc_step, tc_result):
    assert steps.dependency_prerequisite_step(tc_step) == tc_result


def test_prerequisite_step_organize_to_overlay_build_dependency(partitions):
    part = Part("part", {"organize": {"*": "(overlay)/"}}, partitions=partitions)
    organize_dep = Part(
        "organize-dep", {"organize": {"*": "(overlay)/"}}, partitions=partitions
    )
    overlay_dep = Part("overlay-dep", {"overlay-script": "true"}, partitions=partitions)
    normal_dep = Part("normal-dep", {}, partitions=partitions)

    assert (
        steps.dependency_prerequisite_step(
            Step.BUILD, part=part, dependency=organize_dep
        )
        == Step.BUILD
    )
    assert (
        steps.dependency_prerequisite_step(
            Step.BUILD, part=part, dependency=overlay_dep
        )
        == Step.OVERLAY
    )
    assert (
        steps.dependency_prerequisite_step(Step.BUILD, part=part, dependency=normal_dep)
        == Step.STAGE
    )
