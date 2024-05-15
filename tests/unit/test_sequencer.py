# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

import pytest
from craft_parts.actions import Action, ActionProperties, ActionType
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part, PartSpec
from craft_parts.plugins.make_plugin import MakePluginProperties
from craft_parts.sequencer import Sequencer
from craft_parts.state_manager import states
from craft_parts.steps import Step


@pytest.mark.parametrize(
    ("rerun", "action", "reason"),
    [(False, ActionType.SKIP, "already ran"), (True, ActionType.RERUN, "rerun step")],
)
@pytest.mark.parametrize(("step"), [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME])
def test_sequencer_plan(step, action, reason, rerun, mocker, new_dir):
    mocker.patch(
        "craft_parts.state_manager.state_manager.StateManager.has_step_run",
        new=lambda _, x, y: y == step,
    )
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    seq = Sequencer(part_list=[p1], project_info=info)

    seq.plan(step, part_names=["p1"], rerun=rerun)
    actions = [
        Action(part_name="p1", step=s, action_type=ActionType.RUN)
        for s in step.previous_steps()
    ]
    actions.append(Action(part_name="p1", step=step, action_type=action, reason=reason))
    assert seq._actions == actions


def test_sequencer_add_actions(new_dir):
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})

    seq = Sequencer(part_list=[p1], project_info=info)
    seq._add_action(p1, Step.BUILD, reason="some reason")
    seq._add_action(p1, Step.STAGE)

    assert seq._actions == [
        Action(
            part_name="p1",
            step=Step.BUILD,
            action_type=ActionType.RUN,
            reason="some reason",
        ),
        Action(part_name="p1", step=Step.STAGE, action_type=ActionType.RUN),
    ]


@pytest.mark.parametrize(
    ("step", "state_class"),
    [
        (Step.PULL, states.PullState),
        (Step.BUILD, states.BuildState),
        (Step.STAGE, states.StageState),
        (Step.PRIME, states.PrimeState),
    ],
)
def test_sequencer_run_step(step, state_class, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    plugin_props = MakePluginProperties.unmarshal(
        {"source": "src", "make-parameters": ["-Dfoo=bar"]}
    )
    p1 = Part(
        "p1",
        {"plugin": "make", "stage": ["pkg"]},
        plugin_properties=plugin_props,
    )

    seq = Sequencer(part_list=[p1], project_info=info)
    seq._run_step(p1, step)

    stw = seq._sm._state_db.get(part_name="p1", step=step)
    assert stw is not None

    state = stw.state
    assert isinstance(state, state_class)

    # check if action was created
    assert seq._actions == [
        Action(part_name="p1", action_type=ActionType.RUN, step=step)
    ]

    # check if states were updated
    props = PartSpec.unmarshal({"plugin": "make", "stage": ["pkg"]})
    assert state.part_properties == {
        **props.marshal(),
        "source": "src",
        "make-parameters": ["-Dfoo=bar"],
    }
    assert state.project_options == {
        "application_name": "test",
        "arch_triplet": "aarch64-linux-gnu",
        "target_arch": "arm64",
        "project_vars_part_name": None,
        "project_vars": {},
    }


def test_sequencer_run_step_invalid(new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"stage": ["pkg"]})

    seq = Sequencer(part_list=[p1], project_info=info)
    with pytest.raises(RuntimeError) as raised:
        seq._run_step(p1, 999)  # type: ignore[reportGeneralTypeIssues]
    assert str(raised.value) == "invalid step 999"


@pytest.mark.parametrize(
    ("step", "state_class"),
    [
        (Step.PULL, states.PullState),
        (Step.BUILD, states.BuildState),
        (Step.STAGE, states.StageState),
        (Step.PRIME, states.PrimeState),
    ],
)
def test_sequencer_rerun_step(mocker, step, state_class, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"stage": ["pkg"]})

    seq = Sequencer(part_list=[p1], project_info=info)
    mock_clean_part = mocker.spy(seq._sm, "clean_part")

    seq._rerun_step(p1, step)

    # check if clean_part ran
    mock_clean_part.assert_called_once_with(p1, step)

    stw = seq._sm._state_db.get(part_name="p1", step=step)
    assert stw is not None

    state = stw.state
    assert isinstance(state, state_class)

    # check if action was created
    assert seq._actions == [
        Action(part_name="p1", action_type=ActionType.RERUN, step=step)
    ]

    # check if states were updated
    props = PartSpec.unmarshal({"stage": ["pkg"]})
    assert state.part_properties == props.marshal()
    assert state.project_options == {
        "application_name": "test",
        "arch_triplet": "aarch64-linux-gnu",
        "target_arch": "arm64",
        "project_vars_part_name": None,
        "project_vars": {},
    }


@pytest.mark.usefixtures("new_dir")
@pytest.mark.parametrize(
    ("step", "state_class"),
    [
        (Step.PULL, states.PullState),
        (Step.BUILD, states.BuildState),
        (Step.STAGE, states.StageState),
        (Step.PRIME, states.PrimeState),
    ],
)
def test_sequencer_update_step(step, state_class, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    s1 = state_class()
    s1.write(Path("parts/p1/state") / step.name.lower())

    seq = Sequencer(part_list=[p1], project_info=info)

    stw = seq._sm._state_db.get(part_name="p1", step=step)
    assert stw is not None

    seq._update_step(p1, step)

    new_stw = seq._sm._state_db.get(part_name="p1", step=step)
    assert new_stw is not None

    # check if action was created
    assert seq._actions == [
        Action(
            part_name="p1",
            action_type=ActionType.UPDATE,
            step=step,
            properties=ActionProperties(),
        )
    ]

    # check if serial updated
    assert new_stw.is_newer_than(stw)


def test_sequencer_process_dependencies(mocker, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"after": ["p2"]})
    p2 = Part("p2", {})

    seq = Sequencer(part_list=[p1, p2], project_info=info)

    mock_add_all_actions = mocker.patch.object(seq, "_add_all_actions")

    # process p1 dependencies
    seq._process_dependencies(p1, Step.BUILD)
    mock_add_all_actions.assert_called_once_with(
        target_step=Step.STAGE, part_names=["p2"], reason="required to build 'p1'"
    )
