# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2022 Canonical Ltd.
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

"""Part crafter step state management."""

import contextlib
import itertools
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from craft_parts import parts, sources, steps
from craft_parts.infos import ProjectInfo, ProjectVar
from craft_parts.parts import Part
from craft_parts.sources import SourceHandler
from craft_parts.steps import Step

from .reports import Dependency, DirtyReport, OutdatedReport
from .states import StepState, get_step_state_path, load_step_state

logger = logging.getLogger(__name__)


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
        """Retrieve the wrapped state for a given part and step.

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
        :param step_updated: Whether this step should be marked as updated.
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


class StateManager:
    """Keep track of lifecycle execution state.

    The State Manager tells whether a step should run based on current state
    information. The state database is initialized from state on disk, and
    after that it's maintained only in memory.

    :param project_info: The project information.
    :param part_list: A list of this project's parts.
    :param ignore_outdated: A list of file patterns to ignore when testing for
        outdated files.
    """

    def __init__(
        self,
        *,
        project_info: ProjectInfo,
        part_list: List[Part],
        ignore_outdated: Optional[List[str]] = None
    ):
        self._state_db = _StateDB()
        self._project_info = project_info
        self._part_list = part_list
        self._ignore_outdated = ignore_outdated
        self._source_handler_cache: Dict[str, Optional[SourceHandler]] = {}
        self._dirty_report_cache: Dict[Tuple[str, Step], Optional[DirtyReport]] = {}

        part_step_list = _sort_steps_by_state_timestamp(part_list)

        for part, step, _ in part_step_list:
            state = load_step_state(part, step)
            if state:
                self.set_state(part, step, state=state)

    def set_state(self, part: Part, step: Step, *, state: StepState) -> None:
        """Set the state of the given part and step.

        :param part: The part corresponding to the state to be set.
        :param step: The step corresponding to the state to be set.
        """
        stw = self._state_db.wrap_state(state)
        self._state_db.set(part_name=part.name, step=step, state=stw)
        self._dirty_report_cache.pop((part.name, step), None)

    def update_state_timestamp(self, part: Part, step: Step) -> None:
        """Mark the step as recently modified.

        :param part: The part corresponding to the state to update.
        :param step: The step corresponding to the state to update.
        """
        self._state_db.rewrap(part_name=part.name, step=step)

    def clean_part(self, part: Part, step: Step) -> None:
        """Remove the state for this and later steps in the given part.

        :param part: The part corresponding to the state to remove.
        :param step: The step corresponding to the state to remove.
        """
        for next_step in [step] + step.next_steps():
            self._state_db.remove(part_name=part.name, step=next_step)

        self._dirty_report_cache.pop((part.name, step), None)

    def has_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part has already run.

        :param part: The part the step to be verified belongs to.
        :param step: The step to verify.

        :return: Whether the step has already run.
        """
        return self._state_db.test(part_name=part.name, step=step)

    def should_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part should run.

        A given step should run if:
            1. it hasn't already run
            2. it's dirty
            3. it's outdated
            4. either (1), (2), or (3) apply to any earlier steps in the
               part's lifecycle.

        :param part: The part the step to be verified belongs to.
        :param step: The step to verify.

        :return: Whether the step should run.
        """
        if (
            not self.has_step_run(part, step)
            or self.check_if_outdated(part, step) is not None
            or self.check_if_dirty(part, step) is not None
        ):
            return True

        previous_steps = step.previous_steps()
        if previous_steps:
            return self.should_step_run(part, previous_steps[-1])

        return False

    def project_vars(self, part: Part, step: Step) -> Optional[Dict[str, ProjectVar]]:
        """Obtain the project variables for a given part and step.

        :param part: The part corresponding to the state to retrieve.
        :param part: The step corresponding to the state to retrieve.

        :return: The project variables from the last execution.
        """
        stw = self._state_db.get(part_name=part.name, step=step)
        if not stw:
            return {}

        return stw.state.project_options.get("project_vars") or None

    def check_if_outdated(self, part: Part, step: Step) -> Optional[OutdatedReport]:
        """Verify whether a step is outdated.

        A step is considered to be outdated if an earlier step in the lifecycle
        has been run more recently, or if the source code changed on disk.
        This means the step needs to be updated by taking modified files from
        the previous step. This is in contrast to a "dirty" step, which must
        be cleaned and run again.

        :param part: The part the step to be checked belongs to.
        :param step: The step to be checked.

        :return: An class:`OutdatedReport` if the step is outdated, None otherwise.
        """
        logger.debug("check if %s:%s is outdated", part, step)

        if self._state_db.is_step_updated(part_name=part.name, step=step):
            return None

        stw = self._state_db.get(part_name=part.name, step=step)
        if not stw:
            return None

        if step == Step.PULL:
            if part.name in self._source_handler_cache:
                source_handler = self._source_handler_cache[part.name]
            else:
                source_handler = sources.get_source_handler(
                    cache_dir=self._project_info.cache_dir,
                    part=part,
                    project_dirs=self._project_info.dirs,
                    ignore_patterns=self._ignore_outdated,
                )
                self._source_handler_cache[part.name] = source_handler

            state_file = get_step_state_path(part, step)

            if source_handler:
                # Not all sources support checking for updates
                with contextlib.suppress(sources.errors.SourceUpdateUnsupported):
                    if source_handler.check_if_outdated(str(state_file)):
                        return OutdatedReport(source_modified=True)

        elif step == Step.BUILD:
            pull_stw = self._state_db.get(part_name=part.name, step=Step.PULL)

            if pull_stw and pull_stw.is_newer_than(stw):
                return OutdatedReport(previous_step_modified=Step.PULL)

        else:
            for previous_step in reversed(step.previous_steps()):
                # Has a previous step run since this one ran? Then this
                # step needs to be updated.
                previous_stw = self._state_db.get(
                    part_name=part.name, step=previous_step
                )

                if previous_stw and previous_stw.is_newer_than(stw):
                    return OutdatedReport(previous_step_modified=previous_step)

        return None

    def check_if_dirty(self, part: Part, step: Step) -> Optional[DirtyReport]:
        """Verify whether a step is dirty.

        A step is considered to be dirty if relevant properties or project
        options have changed since the step was executed. This means the step
        needs to be cleaned and run again. This is in contrast to an "outdated"
        step, which typically doesn't need to be cleaned, just updated with
        files from an earlier step in the lifecycle.

        :param part: The part the step to be checked belongs to.
        :param step: The step to be checked.

        :return: A class:`DirtyReport` if the step is outdated, None otherwise.
        """
        logger.debug("check if %s:%s is dirty", part, step)

        # If we already have a dirty report, bail
        if (part.name, step) in self._dirty_report_cache:
            return self._dirty_report_cache[(part.name, step)]

        # Retrieve the stored state for this step (assuming it has already run)
        stw = self._state_db.get(part_name=part.name, step=step)
        if not stw:
            # step didn't run yet
            return None

        state = stw.state

        # state contains the old state for this part and step, and we're
        # comparing it to those same properties and options in the current
        # state. If they've changed, then this step is dirty and needs to
        # run again.
        part_properties = part.spec.marshal()
        properties = state.diff_properties_of_interest(part_properties)
        options = state.diff_project_options_of_interest(
            self._project_info.project_options
        )

        if properties or options:
            report = DirtyReport(
                dirty_properties=list(properties),
                dirty_project_options=list(options),
            )
            self._dirty_report_cache[(part.name, step)] = report
            return report

        prerequisite_step = steps.dependency_prerequisite_step(step)
        if not prerequisite_step:
            self._dirty_report_cache[(part.name, step)] = None
            return None

        # The part is clean, check its dependencies

        dependencies = parts.part_dependencies(
            part, part_list=self._part_list, recursive=True
        )

        changed_dependencies: List[Dependency] = []
        for dependency in dependencies:
            prerequisite_stw = self._state_db.get(
                part_name=dependency.name, step=prerequisite_step
            )
            if prerequisite_stw:
                dependency_changed = prerequisite_stw.is_newer_than(stw)
            else:
                dependency_changed = True

            if dependency_changed or self.should_step_run(
                dependency, prerequisite_step
            ):
                changed_dependencies.append(
                    Dependency(part_name=dependency.name, step=prerequisite_step)
                )

        if changed_dependencies:
            report = DirtyReport(changed_dependencies=changed_dependencies)
            self._dirty_report_cache[(part.name, step)] = report
            return report

        self._dirty_report_cache[(part.name, step)] = None
        return None

    def mark_step_updated(self, part: Part, step: Step) -> None:
        """Mark the given part and step as updated.

        :param part: The part being processed.
        :param part: The step being processed.
        """
        self._state_db.rewrap(part_name=part.name, step=step, step_updated=True)

    def get_step_state_overlay_hash(self, part: Part, step: Step) -> bytes:
        """Get the overlay hash from the step state.

        :param part: The part being processed.
        :param part: The step being processed.

        :returns: The hash value for the layer corresponding to the part
            being processed.
        """
        if step not in [Step.BUILD, Step.STAGE]:
            raise ValueError("only BUILD and STAGE states have overlay hash")

        stw = self._state_db.get(part_name=part.name, step=step)
        if not stw:
            # step didn't run yet
            return b""

        overlay_hash = stw.state.overlay_hash  # type: ignore
        if not overlay_hash:
            return b""

        return bytes.fromhex(overlay_hash)


def _sort_steps_by_state_timestamp(
    part_list: List[Part],
) -> List[Tuple[Part, Step, int]]:
    """Sort steps based on state file timestamp.

    Return a sorted list of parts and steps according to the timestamp
    of the state file for the part and step. If there's no corresponding
    state file, the step is ignored.

    :param part_list: The list of all parts whose steps should be sorted.

    :return: The sorted list of tuples containing part, step, and state
        file modification time.
    """
    state_files: List[Tuple[Part, Step, int]] = []
    for part in part_list:
        for step in list(Step):
            path = get_step_state_path(part, step)
            if path.is_file():
                mtime = path.stat().st_mtime_ns
                state_files.append((part, step, mtime))

    return sorted(state_files, key=lambda item: item[2])
