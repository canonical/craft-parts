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
from craft_parts.overlays import LayerHash
from craft_parts.parts import Part, PartSpec
from craft_parts.sequencer import Sequencer
from craft_parts.state_manager import states
from craft_parts.steps import Step


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
        (Step.OVERLAY, states.OverlayState),
        (Step.BUILD, states.BuildState),
        (Step.STAGE, states.StageState),
        (Step.PRIME, states.PrimeState),
    ],
)
def test_sequencer_run_step(step, state_class, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"stage": ["pkg"]})

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
    props = PartSpec.unmarshal({"stage": ["pkg"]})
    assert state.part_properties == props.marshal()
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
        (Step.OVERLAY, states.OverlayState),
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
    if step == Step.OVERLAY:
        mock_clean_part.assert_not_called()
    else:
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
        (Step.OVERLAY, states.OverlayState),
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


def test_sequencer_ensure_overlay_consistency(mocker, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    p2 = Part("p2", {})

    seq = Sequencer(part_list=[p1, p2], project_info=info)

    mock_add_all_actions = mocker.patch.object(seq, "_add_all_actions")

    seq._ensure_overlay_consistency(p1, reason="just a test")

    value = seq._ensure_overlay_consistency(p2, reason="another test")
    mock_add_all_actions.assert_has_calls(
        [
            mocker.call(
                target_step=Step.OVERLAY,
                part_names=["p1"],
                reason="just a test",
            ),
            mocker.call(
                target_step=Step.OVERLAY,
                part_names=["p2"],
                reason="another test",
            ),
        ]
    )
    assert value.hex() == "8d9f437db97f7276a2d68fc44683b6761035f73c"


def test_sequencer_ensure_overlay_consistency_no_run(mocker, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    p2 = Part("p2", {})

    Path("parts/p1/state").mkdir(parents=True)
    layer_hash = LayerHash(bytes.fromhex("6554e32fa718d54160d0511b36f81458e4cb2357"))
    layer_hash.save(p1)

    seq = Sequencer(part_list=[p1, p2], project_info=info)

    mock_add_all_actions = mocker.patch.object(seq, "_add_all_actions")

    value = seq._ensure_overlay_consistency(p2, skip_last=True)
    mock_add_all_actions.assert_not_called()
    assert value.hex() == "8d9f437db97f7276a2d68fc44683b6761035f73c"


def test_sequencer_ensure_overlay_consistency_dont_skip_last(mocker, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    p2 = Part("p2", {})

    Path("parts/p1/state").mkdir(parents=True)
    layer_hash = LayerHash(bytes.fromhex("6554e32fa718d54160d0511b36f81458e4cb2357"))
    layer_hash.save(p1)

    seq = Sequencer(part_list=[p1, p2], project_info=info)

    mock_add_all_actions = mocker.patch.object(seq, "_add_all_actions")

    value = seq._ensure_overlay_consistency(p2)
    mock_add_all_actions.assert_called_once_with(
        target_step=Step.OVERLAY,
        part_names=["p2"],
        reason=None,
    )
    assert value.hex() == "8d9f437db97f7276a2d68fc44683b6761035f73c"


def test_sequencer_ensure_overlay_consistency_rerun(mocker, new_dir):
    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    p2 = Part("p2", {})

    Path("parts/p1/state").mkdir(parents=True)
    layer_hash = LayerHash(
        # echo "some-hash-value" | sha1sum
        bytes.fromhex("4fc928c87171c54a4687d55899ca212d1b1c46e5")
    )
    layer_hash.save(p1)

    seq = Sequencer(part_list=[p1, p2], project_info=info)

    mock_add_all_actions = mocker.patch.object(seq, "_add_all_actions")

    value = seq._ensure_overlay_consistency(p2, reason="test", skip_last=True)
    mock_add_all_actions.assert_called_with(
        target_step=Step.OVERLAY,
        part_names=["p1"],
        reason="test",
    )
    assert value.hex() == "8d9f437db97f7276a2d68fc44683b6761035f73c"


def test_overlay_dependencies_not_dirty(mocker, new_dir):
    mock_reapply = mocker.patch("craft_parts.sequencer.Sequencer._reapply_layer")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text(
        "6554e32fa718d54160d0511b36f81458e4cb2357"
    )

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {})
    p2 = Part("p2", {})
    seq = Sequencer(part_list=[p1, p2], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.OVERLAY)

    assert is_dirty is False
    mock_reapply.assert_not_called()


def test_overlay_dependencies_layer_not_dirty(mocker, new_dir):
    mock_reapply = mocker.patch("craft_parts.sequencer.Sequencer._reapply_layer")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text(
        "9dd8cfd54b554c3a23858ce9ef717f23dd7cae7b"
    )

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.OVERLAY)

    assert is_dirty is False
    mock_reapply.assert_not_called()


def test_overlay_dependencies_layer_reapply(mocker, new_dir):
    mock_reapply = mocker.patch("craft_parts.sequencer.Sequencer._reapply_layer")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text("00000000")

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.OVERLAY)

    assert is_dirty is True
    mock_reapply.assert_called_with(
        p1,
        LayerHash(bytes.fromhex("9dd8cfd54b554c3a23858ce9ef717f23dd7cae7b")),
        reason="previous layer changed",
    )


def test_overlay_dependencies_build_not_dirty(mocker, new_dir):
    mock_rerun = mocker.patch("craft_parts.sequencer.Sequencer._rerun_step")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text("00000000")

    # create build state
    state = states.BuildState(overlay_hash="00000000")
    state.write(Path("parts/p1/state/build"))

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.BUILD)

    assert is_dirty is False
    mock_rerun.assert_not_called()


def test_overlay_dependencies_build_rerun_step(mocker, new_dir):
    mock_rerun = mocker.patch("craft_parts.sequencer.Sequencer._rerun_step")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text("00000000")

    # create build state
    state = states.BuildState(overlay_hash="11111111")
    state.write(Path("parts/p1/state/build"))

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.BUILD)

    assert is_dirty is True
    mock_rerun.assert_called_with(p1, Step.BUILD, reason="overlay changed")


def test_overlay_dependencies_stage_not_dirty(mocker, new_dir):
    mock_rerun = mocker.patch("craft_parts.sequencer.Sequencer._rerun_step")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text("00000000")

    # create build state
    state = states.StageState(overlay_hash="00000000")
    state.write(Path("parts/p1/state/stage"))

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.STAGE)

    assert is_dirty is False
    mock_rerun.assert_not_called()


def test_overlay_dependencies_stage_rerun_step(mocker, new_dir):
    mock_rerun = mocker.patch("craft_parts.sequencer.Sequencer._rerun_step")

    # create p1 layer hash state
    Path("parts/p1/state").mkdir(parents=True)
    Path("parts/p1/state/layer_hash").write_text("00000000")

    # create build state
    state = states.StageState(overlay_hash="11111111")
    state.write(Path("parts/p1/state/stage"))

    info = ProjectInfo(arch="arm64", application_name="test", cache_dir=new_dir)
    p1 = Part("p1", {"overlay-script": "ls"})
    seq = Sequencer(part_list=[p1], project_info=info)

    is_dirty = seq._check_overlay_dependencies(p1, Step.STAGE)

    assert is_dirty is True
    mock_rerun.assert_called_with(p1, Step.STAGE, reason="overlay changed")
