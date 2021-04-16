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

"""Determine the sequence of lifecycle actions to be executed."""

import logging
from typing import Dict, List, Optional, Sequence

from craft_parts import parts, steps
from craft_parts.actions import Action, ActionType
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part, part_list_by_name, sort_parts
from craft_parts.state_manager import StateManager, states
from craft_parts.steps import Step

logger = logging.getLogger(__name__)


class Sequencer:
    """Obtain a list of actions from the parts specification.

    :param part_list: The list of parts to process.
    :param project_info: Information about this project.
    """

    def __init__(self, *, part_list: List[Part], project_info: ProjectInfo):
        self._part_list = sort_parts(part_list)
        self._project_info = project_info
        self._sm = StateManager(project_info=project_info, part_list=part_list)
        self._actions: List[Action] = []

    def plan(self, target_step: Step, part_names: Sequence[str] = None) -> List[Action]:
        """Determine the list of steps to execute for each part.

        :param target_step: The final step to execute for the given part names.
        :param part_names: The names of the parts to process.

        :returns: The list of actions that should be executed.
        """
        self._actions = []
        self._add_all_actions(target_step, part_names)
        return self._actions

    def _add_all_actions(
        self,
        target_step: Step,
        part_names: Sequence[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        selected_parts = part_list_by_name(part_names, self._part_list)

        for current_step in target_step.previous_steps() + [target_step]:
            for part in selected_parts:
                logger.debug("process %s:%s", part.name, current_step)
                self._add_step_actions(
                    current_step=current_step,
                    target_step=target_step,
                    part=part,
                    part_names=part_names,
                    reason=reason,
                )

    def _add_step_actions(
        self,
        *,
        current_step: Step,
        target_step: Step,
        part: Part,
        part_names: Optional[Sequence[str]],
        reason: Optional[str] = None,
    ) -> None:
        # TODO: implement this stub
        pass

    def _process_dependencies(self, part: Part, step: Step) -> None:
        prerequisite_step = steps.dependency_prerequisite_step(step)
        if not prerequisite_step:
            return

        all_deps = parts.part_dependencies(part.name, part_list=self._part_list)

        deps = {p for p in all_deps if self._sm.should_step_run(p, prerequisite_step)}
        for dep in deps:
            self._add_all_actions(
                target_step=prerequisite_step,
                part_names=[dep.name],
                reason=f"required to {_step_verb[step]} {part.name!r}",
            )

    def _run_step(
        self,
        part: Part,
        step: Step,
        *,
        reason: Optional[str] = None,
        rerun: bool = False,
    ) -> None:
        self._process_dependencies(part, step)

        if rerun:
            self._add_action(part, step, action_type=ActionType.RERUN, reason=reason)
        else:
            self._add_action(part, step, reason=reason)

        state: states.StepState
        part_properties = part.spec.marshal()

        if step == Step.PULL:
            state = states.PullState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                assets={},  # TODO: obtain pull assets
            )

        elif step == Step.BUILD:
            state = states.BuildState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                assets={},  # TODO: obtain build assets
            )

        elif step == Step.STAGE:
            state = states.StageState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                files=set(),
                directories=set(),
            )

        else:
            state = states.PrimeState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                files=set(),
                directories=set(),
            )

        self._sm.set_state(part, step, state=state)

    def _rerun_step(
        self, part: Part, step: Step, *, reason: Optional[str] = None
    ) -> None:
        logger.debug("rerun step %s:%s", part.name, step)

        # clean the step and later steps for this part, then run it again
        self._sm.clean_part(part, step)
        self._run_step(part, step, reason=reason, rerun=True)

    def _update_step(self, part: Part, step: Step, *, reason: Optional[str] = None):
        logger.debug("update step %s:%s", part.name, step)
        self._add_action(part, step, action_type=ActionType.UPDATE, reason=reason)
        self._sm.update_state_timestamp(part, step)

    def _add_action(
        self,
        part: Part,
        step: Step,
        *,
        action_type: ActionType = ActionType.RUN,
        reason: Optional[str] = None,
    ) -> None:
        logger.debug("add action %s:%s(%s)", part.name, step, action_type)
        self._actions.append(
            Action(part.name, step, action_type=action_type, reason=reason)
        )


_step_verb: Dict[Step, str] = {
    Step.PULL: "pull",
    Step.BUILD: "build",
    Step.STAGE: "stage",
    Step.PRIME: "prime",
}
