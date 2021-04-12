# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2021 Canonical Ltd.
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

"""Part crafter step state management."""

import itertools
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from craft_parts.steps import Step

from .states import StepState


@dataclass(frozen=True)
class _StateWrapper:
    """A wrapper for the in-memory StepState class with extra metadata.

    This is a wrapper class for StepState that adds additional metadata
    such as the update sequence order to the data loaded from a previous
    lifecycle run. Metadata is read-only to prevent unintentional changes.
    """

    state: StepState
    serial: int
    step_updated: bool = False

    def is_newer_than(self, other: "_StateWrapper"):
        """Verify if this state is newer than the specified state.

        :param other: The wrapped state to compare this state to.
        """
        return self.serial > other.serial


class _StateDB:
    """A dictionary-backed simple database manager for wrapped states."""

    def __init__(self):
        self._state: Dict[Tuple[str, Step], _StateWrapper] = {}
        self._serial_gen = itertools.count(1)

    def wrap_state(
        self, state: StepState, *, step_updated: bool = False
    ) -> _StateWrapper:
        """Add metadata to step state.

        :param state: The part state to store.
        :param step_updated: Whether this state was updated after an
            outdated report.

        :return: The wrapped state with additional metadata.
        """
        stw = _StateWrapper(
            state, serial=next(self._serial_gen), step_updated=step_updated
        )
        return stw

    def set(
        self, *, part_name: str, step: Step, state: Optional[_StateWrapper]
    ) -> None:
        """Set a state for a given part and step.

        :param part_name: The name of the part corresponding to the state
            to be set.
        :param step: The step corresponding to the state to be set.
        :param state: The state to assign to the part name and step.
        """
        if not state:
            self.remove(part_name=part_name, step=step)
            return

        self._state[(part_name, step)] = state

    def get(self, *, part_name: str, step: Step) -> Optional[_StateWrapper]:
        """Retrieve the state for a given part and step.

        :param part_name: The name of the part corresponding to the state
            to be retrieved.
        :param step: The step corresponding to the state to be retrieved.

        :return: The wrapped state assigned to the part name and step.
        """
        return self._state.get((part_name, step))

    def test(self, *, part_name: str, step: Step) -> bool:
        """Verify if there is a state defined for a given part and step.

        :param part_name: The name of the part corresponding to the state
            to be tested.
        :param step: The step corresponding to the state to be tested.

        :return: Whether a state is defined for the part name and step.
        """
        return self._state.get((part_name, step)) is not None

    def remove(self, *, part_name: str, step: Step) -> None:
        """Remove the state for a given part and step.

        :param part_name: The name of the part corresponding to the state
            to be removed.
        :param step: The step corresponding to the state to be removed.
        """
        self._state.pop((part_name, step), None)

    def rewrap(self, *, part_name: str, step: Step, step_updated: bool = False) -> None:
        """Rewrap an existing state, updating its metadata.

        :param part_name: The name of the part corresponding to the state
            to be rewrapped.
        :param step: The step corresponding to the state to be rewrapped.
        """
        stw = self.get(part_name=part_name, step=step)
        if stw:
            # rewrap the state with new metadata
            new_stw = self.wrap_state(stw.state, step_updated=step_updated)
            self.set(part_name=part_name, step=step, state=new_stw)

    def is_step_updated(self, *, part_name: str, step: Step) -> bool:
        """Verify whether the part and step was updated.

        The ``step_updated`` status is set when an outdated step is scheduled to
        be updated. This is stored as state metadata because updating data on
        disk only happens in the execution phase).

        :param part_name: The name of the part whose step will be verified.
        :param step: The step to verify.

        :return: Whether the step was updated.
        """
        stw = self.get(part_name=part_name, step=step)
        if stw:
            return stw.step_updated
        return False
