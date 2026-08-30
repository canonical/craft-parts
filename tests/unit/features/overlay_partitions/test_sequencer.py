# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

from craft_parts.actions import Action, ActionType
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.sequencer import Sequencer
from craft_parts.steps import Step


def test_sequencer_add_actions(new_dir):
    partitions = ["default"]
    info = ProjectInfo(
        application_name="test", cache_dir=new_dir, partitions=partitions
    )
    p1 = Part("p1", {"organize": {"foo": "(overlay)/bar"}}, partitions=partitions)
    p2 = Part("p2", {}, partitions=partitions)
    p3 = Part("p3", {}, partitions=partitions)

    seq = Sequencer(part_list=[p1, p2, p3], project_info=info)
    actions = seq.plan(Step.BUILD, part_names=["p1", "p2", "p3"])

    assert actions == [
        Action(
            part_name="p1",
            step=Step.PULL,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p2",
            step=Step.PULL,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p3",
            step=Step.PULL,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p1",
            step=Step.OVERLAY,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p1",
            step=Step.BUILD,
            action_type=ActionType.RUN,
            reason="organize contents to overlay",
        ),
        Action(
            part_name="p2",
            step=Step.OVERLAY,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p3",
            step=Step.OVERLAY,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p1",
            step=Step.BUILD,
            action_type=ActionType.SKIP,
            reason="already ran",
        ),
        Action(
            part_name="p2",
            step=Step.BUILD,
            action_type=ActionType.RUN,
        ),
        Action(
            part_name="p3",
            step=Step.BUILD,
            action_type=ActionType.RUN,
        ),
    ]
