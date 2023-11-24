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

import dataclasses
from pathlib import Path

import pytest
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.state_manager import StateManager, state_manager, states
from craft_parts.steps import Step
from craft_parts.utils import os_utils


class TestStateWrapper:
    """Check _StateWrapper initialization and methods."""

    def test_state_wrapping(self, properties):
        state = states.PullState(part_properties=properties)
        stw = state_manager._StateWrapper(state=state, serial=500)
        assert stw.state == state
        assert stw.serial == 500
        assert stw.step_updated is False

    def test_step_updated(self, properties):
        state = states.PullState(part_properties=properties)
        stw = state_manager._StateWrapper(state=state, serial=42, step_updated=True)
        assert stw.state == state
        assert stw.serial == 42
        assert stw.step_updated is True

    @pytest.mark.parametrize(
        ("s1", "s2", "result"),
        [
            (0, 0, False),
            (0, 1, False),
            (1, 0, True),
        ],
    )
    def test_newer_comparison(self, s1, s2, result):
        state = states.PullState()
        stw = state_manager._StateWrapper(state=state, serial=s1)
        other = state_manager._StateWrapper(state=state, serial=s2)
        assert stw.is_newer_than(other) == result

    def test_frozen_data(self, properties):
        state = states.PullState(part_properties=properties)
        stw = state_manager._StateWrapper(state=state, serial=500)

        with pytest.raises(dataclasses.FrozenInstanceError):
            stw.state = states.PullState()  # type: ignore[reportGeneralTypeIssues]

        with pytest.raises(dataclasses.FrozenInstanceError):
            stw.serial = 5  # type: ignore[reportGeneralTypeIssues]

        with pytest.raises(dataclasses.FrozenInstanceError):
            stw.step_updated = True  # type: ignore[reportGeneralTypeIssues]


class TestStateDB:
    """Check _StateDB initialization and methods."""

    def test_wrap_state(self):
        state = states.PullState()

        sdb = state_manager._StateDB()
        stw = sdb.wrap_state(state)
        assert stw.state == state
        assert stw.serial == 1
        assert stw.step_updated is False

        other = sdb.wrap_state(state, step_updated=True)
        assert other.serial == 2
        assert other.step_updated is True

    def test_state_access(self):
        state = states.PullState()
        sdb = state_manager._StateDB()
        stw = sdb.wrap_state(state)

        # test & retrieve non-existing state
        assert sdb.test(part_name="foo", step=Step.PULL) is False
        assert sdb.get(part_name="foo", step=Step.PULL) is None

        # delete non-existing state shouldn't fail
        sdb.remove(part_name="foo", step=Step.PULL)

        # insert state
        sdb.set(part_name="foo", step=Step.PULL, state=stw)
        assert sdb.test(part_name="foo", step=Step.PULL) is True
        assert sdb.get(part_name="foo", step=Step.PULL) == stw

        # delete state
        sdb.remove(part_name="foo", step=Step.PULL)
        assert sdb.test(part_name="foo", step=Step.PULL) is False
        assert sdb.get(part_name="foo", step=Step.PULL) is None

    def test_reinsert_state(self):
        state = states.PullState()
        sdb = state_manager._StateDB()
        stw = sdb.wrap_state(state)

        # insert a state
        sdb.set(part_name="foo", step=Step.PULL, state=stw)
        assert sdb.test(part_name="foo", step=Step.PULL) is True
        assert sdb.get(part_name="foo", step=Step.PULL) == stw

        # insert a new state
        new_stw = sdb.wrap_state(state)
        assert stw != new_stw

        sdb.set(part_name="foo", step=Step.PULL, state=new_stw)
        assert sdb.test(part_name="foo", step=Step.PULL) is True
        assert sdb.get(part_name="foo", step=Step.PULL) == new_stw

        # insert None is equivalent to delete
        sdb.set(part_name="foo", step=Step.PULL, state=None)
        assert sdb.test(part_name="foo", step=Step.PULL) is False
        assert sdb.get(part_name="foo", step=Step.PULL) is None

    def test_rewrap_state(self):
        state = states.PullState()
        sdb = state_manager._StateDB()
        stw = sdb.wrap_state(state)

        assert stw.serial == 1

        # rewrap a non-existing state shouldn't fail
        assert sdb.test(part_name="foo", step=Step.PULL) is False
        sdb.rewrap(part_name="foo", step=Step.PULL)
        assert sdb.test(part_name="foo", step=Step.PULL) is False

        # a new state is created
        new_stw = sdb.wrap_state(state)
        assert new_stw.serial == 2

        # insert and rewrap the existing state
        sdb.set(part_name="foo", step=Step.PULL, state=stw)
        sdb.rewrap(part_name="foo", step=Step.PULL)
        assert sdb.is_step_updated(part_name="foo", step=Step.PULL) is False

        rewrapped_stw = sdb.get(part_name="foo", step=Step.PULL)
        assert rewrapped_stw is not None
        assert rewrapped_stw.serial == 3

    def test_set_step_updated(self):
        state = states.PullState()
        sdb = state_manager._StateDB()
        stw = sdb.wrap_state(state)

        assert stw.serial == 1

        # checking update status of a non-existing state shouldn't fail
        assert sdb.is_step_updated(part_name="foo", step=Step.PULL) is False

        # insert a new state
        sdb.set(part_name="foo", step=Step.PULL, state=stw)
        assert sdb.is_step_updated(part_name="foo", step=Step.PULL) is False

        # set the step updated flag
        sdb.rewrap(part_name="foo", step=Step.PULL, step_updated=True)
        assert sdb.is_step_updated(part_name="foo", step=Step.PULL) is True

        rewrapped_stw = sdb.get(part_name="foo", step=Step.PULL)
        assert rewrapped_stw is not None
        assert rewrapped_stw.serial == 2


class TestStateManager:
    """Verify if the State Manager is correctly tracking state changes."""

    def test_has_step_run(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        p3 = Part("p3", {})

        s3 = states.StageState()
        s3.write(Path("parts/p3/state/stage"))

        # only p3:stage has a state file when the stage manager is created
        sm = StateManager(project_info=info, part_list=[p1, p2, p3])

        for part in [p1, p2, p3]:
            for step in list(Step):
                ran = sm.has_step_run(part, step)
                assert ran == (part == p3 and step == Step.STAGE)

    def test_set_state(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        p2 = Part("p2", {})
        p3 = Part("p3", {})

        # no state files when the stage manager is created
        sm = StateManager(project_info=info, part_list=[p1, p2, p3])

        for part in [p1, p2, p3]:
            for step in list(Step):
                ran = sm.has_step_run(part, step)
                assert ran is False

        # a state is assigned to p2:build (no state file)
        s2 = states.BuildState()
        sm.set_state(p2, Step.BUILD, state=s2)

        for part in [p1, p2, p3]:
            for step in list(Step):
                ran = sm.has_step_run(part, step)
                assert ran == (part == p2 and step == Step.BUILD)

    def test_update_state_timestamp(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        sm.set_state(p1, Step.PULL, state=states.PullState())
        sm.set_state(p1, Step.BUILD, state=states.BuildState())

        # state 1 is older than state 2
        stw1 = sm._state_db.get(part_name="p1", step=Step.PULL)
        stw2 = sm._state_db.get(part_name="p1", step=Step.BUILD)
        assert stw1 is not None
        assert stw2 is not None
        assert stw2.is_newer_than(stw1)

        # update the timestamp of state 1
        sm.update_state_timestamp(p1, Step.PULL)

        # now state 1 is newer than state 2
        stw1 = sm._state_db.get(part_name="p1", step=Step.PULL)
        assert stw1 is not None
        assert stw1.is_newer_than(stw2)

    def test_clean_part(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        # add states for all steps
        sm.set_state(p1, Step.PULL, state=states.PullState())
        sm.set_state(p1, Step.BUILD, state=states.BuildState())
        sm.set_state(p1, Step.STAGE, state=states.StageState())
        sm.set_state(p1, Step.PRIME, state=states.PrimeState())

        # make sure steps were added to the database
        for step in [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME]:
            assert sm._state_db.get(part_name="p1", step=step) is not None

        # now clean the first step
        sm.clean_part(p1, Step.PULL)

        # all steps are now gone
        for step in list(Step):
            assert sm._state_db.get(part_name="p1", step=step) is None

    def test_clean_part_overlay_enabled(self, enable_overlay_feature, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        # add states for all steps
        sm.set_state(p1, Step.PULL, state=states.PullState())
        sm.set_state(p1, Step.OVERLAY, state=states.OverlayState())
        sm.set_state(p1, Step.BUILD, state=states.BuildState())
        sm.set_state(p1, Step.STAGE, state=states.StageState())
        sm.set_state(p1, Step.PRIME, state=states.PrimeState())

        # make sure steps were added to the database
        for step in list(Step):
            assert sm._state_db.get(part_name="p1", step=step) is not None

        # now clean the first step
        sm.clean_part(p1, Step.PULL)

        # all steps are now gone
        for step in list(Step):
            assert sm._state_db.get(part_name="p1", step=step) is None

    def test_should_step_run_trivial(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            assert sm.should_step_run(p1, step) is True

    def test_should_step_run_step_already_ran(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        part_properties = p1.spec.marshal()

        # p1 pull already ran
        s1 = states.StageState(part_properties=part_properties)
        s1.write(Path("parts/p1/state/pull"))

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            assert sm.should_step_run(p1, step) == (step != Step.PULL)

    def test_should_step_run_outdated(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        part_properties = p1.spec.marshal()

        # p1 overlay already ran
        s1 = states.OverlayState(part_properties=part_properties)
        s1.write(Path("parts/p1/state/overlay"))

        # but p1 pull ran more recently
        s1 = states.PullState(part_properties=part_properties)
        s1.write(Path("parts/p1/state/pull"))

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            assert sm.should_step_run(p1, step) == (step > Step.PULL)

        # and we updated it!
        sm._state_db.rewrap(part_name="p1", step=Step.OVERLAY, step_updated=True)

        for step in list(Step):
            assert sm.should_step_run(p1, step) == (step >= Step.BUILD)

    def test_should_step_run_dirty(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        part_properties = p1.spec.marshal()

        # p1 pull, overlay and build already ran
        s1 = states.PullState(part_properties=part_properties)
        s1.write(Path("parts/p1/state/pull"))
        s2 = states.OverlayState(part_properties=part_properties)
        s2.write(Path("parts/p1/state/overlay"))
        s3 = states.BuildState(part_properties=part_properties)
        s3.write(Path("parts/p1/state/build"))

        sm = StateManager(project_info=info, part_list=[p1])

        # we're clean, steps STAGE and PRIME should run
        for step in list(Step):
            assert sm.should_step_run(p1, step) == (step > Step.BUILD)

        # make the build step dirty
        # this only happens between runs so recreate the state manager
        sm = StateManager(project_info=info, part_list=[p1])
        stw = sm._state_db.get(part_name="p1", step=Step.BUILD)
        assert stw is not None

        stw.state.part_properties["build-packages"] = ["new_pkg"]

        # now build should run again
        for step in list(Step):
            assert sm.should_step_run(p1, step) == (step >= Step.BUILD)


class TestStepOutdated:
    """Verify outdated step checks."""

    def test_not_outdated(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            assert sm.check_if_outdated(p1, step) is None

    def test_outdated(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        # p1 build already ran
        s1 = states.BuildState()
        s1.write(Path("parts/p1/state/build"))

        # but p1 pull ran more recently
        s1 = states.StageState()
        s1.write(Path("parts/p1/state/pull"))

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            report = sm.check_if_outdated(p1, step)
            if step == Step.BUILD:
                assert report is not None
                assert report.reason() == "'PULL' step changed"
            else:
                assert report is None

        # and we updated it!
        sm._state_db.rewrap(part_name="p1", step=Step.BUILD, step_updated=True)

        for step in list(Step):
            assert sm.check_if_outdated(p1, step) is None

    def test_source_outdated(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {"source": "subdir"})  # source is local

        # p1 pull ran
        s1 = states.StageState()
        s1.write(Path("parts/p1/state/pull"))

        Path("subdir").mkdir()
        os_utils.TimedWriter.write_text(Path("subdir/foo"), "content")

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            report = sm.check_if_outdated(p1, step)
            if step == Step.PULL:
                assert report is not None
                assert report.reason() == "source changed"
            else:
                assert report is None

        # and we updated it!
        sm._state_db.rewrap(part_name="p1", step=Step.PULL, step_updated=True)

        for step in list(Step):
            assert sm.check_if_outdated(p1, step) is None

    def test_source_outdated_ignored(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {"source": "subdir"})  # source is local

        # p1 pull ran
        s1 = states.StageState()
        s1.write(Path("parts/p1/state/pull"))

        Path("subdir").mkdir()
        os_utils.TimedWriter.write_text(Path("subdir/foo"), "content")

        sm = StateManager(project_info=info, part_list=[p1], ignore_outdated=["foo*"])

        for step in list(Step):
            report = sm.check_if_outdated(p1, step)
            assert report is None


class TestStepDirty:
    """Verify dirty step checks."""

    def test_not_dirty(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})

        sm = StateManager(project_info=info, part_list=[p1])

        for step in list(Step):
            assert sm.check_if_dirty(p1, step) is None

    def test_dirty_property(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {})
        part_properties = p1.spec.marshal()

        # p1 pull and build already ran
        s1 = states.PullState(part_properties=part_properties)
        s1.write(Path("parts/p1/state/pull"))
        s2 = states.BuildState(part_properties=part_properties)
        s2.write(Path("parts/p1/state/build"))

        sm = StateManager(project_info=info, part_list=[p1])

        # check if dirty, all steps are clean
        for step in list(Step):
            assert sm.check_if_dirty(p1, step) is None

        # make the build step dirty
        # this only happens between runs so recreate the state manager
        sm = StateManager(project_info=info, part_list=[p1])
        stw = sm._state_db.get(part_name="p1", step=Step.BUILD)
        assert stw is not None

        stw.state.part_properties["build-packages"] = ["new_pkg"]

        # now check again if dirty
        for step in list(Step):
            report = sm.check_if_dirty(p1, step)
            if step == Step.BUILD:
                assert report is not None
                assert report.reason() == "'build-packages' property changed"
            else:
                assert report is None

    def test_dirty_dependency(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {"after": ["p2"]})
        p1_properties = p1.spec.marshal()
        p2 = Part("p2", {})
        p2_properties = p2.spec.marshal()

        # p2 pull/overlay/build/stage already ran
        s2 = states.PullState(part_properties=p2_properties)
        s2.write(Path("parts/p2/state/pull"))
        s2 = states.OverlayState(part_properties=p2_properties)
        s2.write(Path("parts/p2/state/overlay"))
        s2 = states.BuildState(part_properties=p2_properties)
        s2.write(Path("parts/p2/state/build"))
        s2 = states.StageState(part_properties=p2_properties)
        s2.write(Path("parts/p2/state/stage"))

        # p1 pull/overlay/build already ran
        s1 = states.PullState(part_properties=p1_properties)
        s1.write(Path("parts/p1/state/pull"))
        s1 = states.OverlayState(part_properties=p1_properties)
        s1.write(Path("parts/p1/state/overlay"))
        s1 = states.BuildState(part_properties=p1_properties)
        s1.write(Path("parts/p1/state/build"))

        sm = StateManager(project_info=info, part_list=[p1, p2])

        # check if dirty, all steps are clean
        for part in [p1, p2]:
            for step in list(Step):
                assert sm.check_if_dirty(part, step) is None

        # make p2 stage step dirty
        # this only happens between runs so recreate the state manager
        sm = StateManager(project_info=info, part_list=[p1, p2])
        stw = sm._state_db.get(part_name="p2", step=Step.STAGE)
        assert stw is not None

        stw.state.part_properties["stage"] = ["new_entry"]

        # now check if p1:build is dirty
        for step in list(Step):
            report = sm.check_if_dirty(p1, step)
            if step == Step.BUILD:
                assert report is not None
                assert report.reason() == "stage for part 'p2' changed"
            else:
                assert report is None

        # and if p2:stage is also dirty
        for step in list(Step):
            report = sm.check_if_dirty(p2, step)
            if step == Step.STAGE:
                assert report is not None
                assert report.reason() == "'stage' property changed"
            else:
                assert report is None

    def test_dirty_dependency_didnt_run(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        p1 = Part("p1", {"after": ["p2"]})
        p1_properties = p1.spec.marshal()
        p2 = Part("p2", {})

        # p1 pull/build already ran
        s1 = states.PullState(part_properties=p1_properties)
        s1.write(Path("parts/p1/state/pull"))
        s1 = states.BuildState(part_properties=p1_properties)
        s1.write(Path("parts/p1/state/build"))

        sm = StateManager(project_info=info, part_list=[p1, p2])

        # check if dirty
        for step in list(Step):
            report = sm.check_if_dirty(p1, step)
            if step == Step.BUILD:
                assert report is not None
                assert report.reason() == "stage for part 'p2' changed"
            else:
                assert report is None


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify State Manager helper functions."""

    def test_state_sort(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})

        s1 = states.PullState()
        s2 = states.BuildState()
        s3 = states.PullState()
        s4 = states.PrimeState()

        # create state files
        # use 20ms interval to avoid creating files with the same timestamp on
        # systems with low ticks resolution
        s4.write(Path("parts/bar/state/prime"))
        s3.write(Path("parts/bar/state/pull"))
        s1.write(Path("parts/foo/state/pull"))
        s2.write(Path("parts/foo/state/build"))

        slist = state_manager._sort_steps_by_state_timestamp([p1, p2])
        assert [x[0:2] for x in slist] == [
            (p2, Step.PRIME),
            (p2, Step.PULL),
            (p1, Step.PULL),
            (p1, Step.BUILD),
        ]
