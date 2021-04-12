# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import dataclasses

import pytest

from craft_parts.state_manager import state_manager, states
from craft_parts.steps import Step


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
        "s1,s2,result",
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
            stw.state = states.PullState()  # type: ignore

        with pytest.raises(dataclasses.FrozenInstanceError):
            stw.serial = 5  # type: ignore

        with pytest.raises(dataclasses.FrozenInstanceError):
            stw.step_updated = True  # type: ignore


class TestEphemeralStates:
    """Check _EphemeralStates initialization and methods."""

    def test_wrap_state(self):
        state = states.PullState()

        eph = state_manager._EphemeralStates()
        stw = eph.wrap_state(state)
        assert stw.state == state
        assert stw.serial == 1
        assert stw.step_updated is False

        other = eph.wrap_state(state, step_updated=True)
        assert other.serial == 2
        assert other.step_updated is True

    def test_state_access(self):
        state = states.PullState()
        eph = state_manager._EphemeralStates()
        stw = eph.wrap_state(state)

        # test & retrieve non-existing state
        assert eph.test(part_name="foo", step=Step.PULL) is False
        assert eph.get(part_name="foo", step=Step.PULL) is None

        # delete non-existing state shouldn't fail
        eph.remove(part_name="foo", step=Step.PULL)

        # insert state
        eph.set(part_name="foo", step=Step.PULL, state=stw)
        assert eph.test(part_name="foo", step=Step.PULL) is True
        assert eph.get(part_name="foo", step=Step.PULL) == stw

        # delete state
        eph.remove(part_name="foo", step=Step.PULL)
        assert eph.test(part_name="foo", step=Step.PULL) is False
        assert eph.get(part_name="foo", step=Step.PULL) is None

    def test_reinsert_state(self):
        state = states.PullState()
        eph = state_manager._EphemeralStates()
        stw = eph.wrap_state(state)

        # insert a state
        eph.set(part_name="foo", step=Step.PULL, state=stw)
        assert eph.test(part_name="foo", step=Step.PULL) is True
        assert eph.get(part_name="foo", step=Step.PULL) == stw

        # insert a new state
        new_stw = eph.wrap_state(state)
        assert stw != new_stw

        eph.set(part_name="foo", step=Step.PULL, state=new_stw)
        assert eph.test(part_name="foo", step=Step.PULL) is True
        assert eph.get(part_name="foo", step=Step.PULL) == new_stw

        # insert None is equivalent to delete
        eph.set(part_name="foo", step=Step.PULL, state=None)
        assert eph.test(part_name="foo", step=Step.PULL) is False
        assert eph.get(part_name="foo", step=Step.PULL) is None

    def test_rewrap_state(self):
        state = states.PullState()
        eph = state_manager._EphemeralStates()
        stw = eph.wrap_state(state)

        assert stw.serial == 1

        # rewrap a non-existing state shouldn't fail
        assert eph.test(part_name="foo", step=Step.PULL) is False
        eph.rewrap(part_name="foo", step=Step.PULL)
        assert eph.test(part_name="foo", step=Step.PULL) is False

        # a new state is created
        new_stw = eph.wrap_state(state)
        assert new_stw.serial == 2

        # insert and rewrap the existing state
        eph.set(part_name="foo", step=Step.PULL, state=stw)
        eph.rewrap(part_name="foo", step=Step.PULL)
        assert eph.is_step_updated(part_name="foo", step=Step.PULL) is False

        rewrapped_stw = eph.get(part_name="foo", step=Step.PULL)
        assert rewrapped_stw.serial == 3

    def test_set_step_updated(self):
        state = states.PullState()
        eph = state_manager._EphemeralStates()
        stw = eph.wrap_state(state)

        assert stw.serial == 1

        # checking update status of a non-existing state shouldn't fail
        assert eph.is_step_updated(part_name="foo", step=Step.PULL) is False

        # insert a new state
        eph.set(part_name="foo", step=Step.PULL, state=stw)
        assert eph.is_step_updated(part_name="foo", step=Step.PULL) is False

        # set the step updated flag
        eph.rewrap(part_name="foo", step=Step.PULL, step_updated=True)
        assert eph.is_step_updated(part_name="foo", step=Step.PULL) is True

        rewrapped_stw = eph.get(part_name="foo", step=Step.PULL)
        assert rewrapped_stw.serial == 2
