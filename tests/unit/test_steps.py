# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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
from craft_parts.steps import Step


def test_step():
    assert f"{Step.PULL!r}" == "Step.PULL"
    assert f"{Step.OVERLAY!r}" == "Step.OVERLAY"
    assert f"{Step.BUILD!r}" == "Step.BUILD"
    assert f"{Step.STAGE!r}" == "Step.STAGE"
    assert f"{Step.PRIME!r}" == "Step.PRIME"


def test_ordering():
    slist = list(Step)
    assert sorted(slist) == [
        Step.PULL,
        Step.OVERLAY,
        Step.BUILD,
        Step.STAGE,
        Step.PRIME,
    ]


@pytest.mark.parametrize(
    ("tc_step", "tc_result"),
    [
        (Step.PULL, []),
        (Step.BUILD, [Step.PULL]),
        (Step.STAGE, [Step.PULL, Step.BUILD]),
        (Step.PRIME, [Step.PULL, Step.BUILD, Step.STAGE]),
    ],
)
def test_previous_steps(tc_step, tc_result):
    assert tc_step.previous_steps() == tc_result


@pytest.mark.parametrize(
    ("tc_step", "tc_result"),
    [
        (Step.PULL, [Step.BUILD, Step.STAGE, Step.PRIME]),
        (Step.BUILD, [Step.STAGE, Step.PRIME]),
        (Step.STAGE, [Step.PRIME]),
        (Step.PRIME, []),
    ],
)
def test_next_steps(tc_step, tc_result):
    assert tc_step.next_steps() == tc_result


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
