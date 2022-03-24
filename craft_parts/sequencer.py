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

"""Determine the sequence of lifecycle actions to be executed."""

import logging
from typing import Dict, List, Optional, Sequence, Set

from craft_parts import parts, steps
from craft_parts.actions import Action, ActionType
from craft_parts.infos import ProjectInfo, ProjectVar
from craft_parts.overlays import LayerHash, LayerStateManager
from craft_parts.parts import Part, part_list_by_name, sort_parts
from craft_parts.state_manager import StateManager, states
from craft_parts.steps import Step

logger = logging.getLogger(__name__)


class Sequencer:
    """Obtain a list of actions from the parts specification.

    The sequencer takes the parts definition and the current state of a project
    to plan all the actions needed to reach a given target step. State is read
    from persistent storage and updated entirely in memory. Sequencer operations
    never change disk contents.

    :param part_list: The list of parts to process.
    :param project_info: Information about this project.
    :param ignore_outdated: A list of file patterns to ignore when testing for
        outdated files.
    """

    def __init__(
        self,
        *,
        part_list: List[Part],
        project_info: ProjectInfo,
        ignore_outdated: Optional[List[str]] = None,
        base_layer_hash: Optional[LayerHash] = None,
    ):
        self._part_list = sort_parts(part_list)
        self._project_info = project_info
        self._sm = StateManager(
            project_info=project_info,
            part_list=part_list,
            ignore_outdated=ignore_outdated,
        )
        self._layer_state = LayerStateManager(self._part_list, base_layer_hash)
        self._actions: List[Action] = []

        self._overlay_viewers: Set[Part] = set()
        for part in part_list:
            if parts.has_overlay_visibility(
                part, viewers=self._overlay_viewers, part_list=part_list
            ):
                self._overlay_viewers.add(part)

    def plan(
        self, target_step: Step, part_names: Optional[Sequence[str]] = None
    ) -> List[Action]:
        """Determine the list of steps to execute for each part.

        :param target_step: The final step to execute for the given part names.
        :param part_names: The names of the parts to process.

        :returns: The list of actions that should be executed.
        """
        self._actions = []
        self._add_all_actions(target_step, part_names)
        return self._actions

    def reload_state(self) -> None:
        """Reload state from persistent storage."""
        self._sm = StateManager(
            project_info=self._project_info, part_list=self._part_list
        )

    def _add_all_actions(
        self,
        target_step: Step,
        part_names: Optional[Sequence[str]] = None,
        reason: Optional[str] = None,
    ) -> None:
        selected_parts = part_list_by_name(part_names, self._part_list)
        if not selected_parts:
            return

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
        """Verify if this step should be executed."""
        # check if step already ran, if not then run it
        if not self._sm.has_step_run(part, current_step):
            self._run_step(part, current_step, reason=reason)
            return

        # If the step has already run:
        #
        # 1. If the step is the exact step that was requested, and the part was
        #    explicitly listed, run it again.

        if part_names and current_step == target_step and part.name in part_names:
            if not reason:
                reason = "requested step"
            self._rerun_step(part, current_step, reason=reason)
            return

        # 2. If the step is dirty, run it again. A step is considered dirty if
        #    properties used by the step have changed, project options have changed,
        #    or dependencies have been re-staged.

        dirty_report = self._sm.check_if_dirty(part, current_step)
        if dirty_report:
            logger.debug("%s:%s is dirty", part.name, current_step)
            self._rerun_step(part, current_step, reason=dirty_report.reason())
            return

        # 3. If the step depends on overlay, check if layers are dirty and reapply
        #    layers (if step is overlay) or re-execute the step (if step is build
        #    or stage).
        if self._check_overlay_dependencies(part, current_step):
            return

        # 4. If the step is outdated, run it again (without cleaning if possible).
        #    A step is considered outdated if an earlier step in the lifecycle
        #    has been re-executed.

        outdated_report = self._sm.check_if_outdated(part, current_step)
        if outdated_report:
            logger.debug("%s:%s is outdated", part.name, current_step)

            if current_step in (Step.PULL, Step.OVERLAY, Step.BUILD):
                self._update_step(part, current_step, reason=outdated_report.reason())
            else:
                self._rerun_step(part, current_step, reason=outdated_report.reason())

            self._sm.mark_step_updated(part, current_step)
            return

        # 5. Otherwise skip it. Note that this action must always be sent to the
        #    executor to update project variables.
        self._add_action(
            part,
            current_step,
            action_type=ActionType.SKIP,
            reason="already ran",
            project_vars=self._sm.project_vars(part, current_step),
        )

    def _process_dependencies(self, part: Part, step: Step) -> None:
        prerequisite_step = steps.dependency_prerequisite_step(step)
        if not prerequisite_step:
            return

        all_deps = parts.part_dependencies(part, part_list=self._part_list)
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

        if step == Step.OVERLAY:
            # Make sure all previous layers are in place before we add a new
            # layer to the overlay stack,
            layer_hash = self._ensure_overlay_consistency(
                part,
                reason=f"required to overlay {part.name!r}",
                skip_last=True,
            )
            self._layer_state.set_layer_hash(part, layer_hash)

        elif (step == Step.BUILD and part in self._overlay_viewers) or (
            step == Step.STAGE and part.has_overlay
        ):
            # The overlay step for all parts should run before we build a part
            # with overlay visibility or before we stage a part that declares
            # overlay parameters.
            last_part = self._part_list[-1]
            verb = _step_verb[step]
            self._ensure_overlay_consistency(
                last_part,
                reason=f"required to {verb} {part.name!r}",
            )

        if rerun:
            self._add_action(part, step, action_type=ActionType.RERUN, reason=reason)
        else:
            self._add_action(part, step, reason=reason)

        state: states.StepState
        part_properties = part.spec.marshal()

        # create step state

        if step == Step.PULL:
            state = states.PullState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
            )

        elif step == Step.OVERLAY:
            state = states.OverlayState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
            )

        elif step == Step.BUILD:
            state = states.BuildState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                overlay_hash=self._layer_state.get_overlay_hash().hex(),
            )

        elif step == Step.STAGE:
            state = states.StageState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
                overlay_hash=self._layer_state.get_overlay_hash().hex(),
            )

        elif step == Step.PRIME:
            state = states.PrimeState(
                part_properties=part_properties,
                project_options=self._project_info.project_options,
            )

        else:
            raise RuntimeError(f"invalid step {step!r}")

        self._sm.set_state(part, step, state=state)

    def _rerun_step(
        self, part: Part, step: Step, *, reason: Optional[str] = None
    ) -> None:
        """Clean existing state and reexecute the step."""
        logger.debug("rerun step %s:%s", part.name, step)

        if step != Step.OVERLAY:
            # clean the step and later steps for this part
            self._sm.clean_part(part, step)

        self._run_step(part, step, reason=reason, rerun=True)

    def _update_step(self, part: Part, step: Step, *, reason: Optional[str] = None):
        """Set the step state as reexecuted by updating its timestamp."""
        logger.debug("update step %s:%s", part.name, step)
        self._add_action(part, step, action_type=ActionType.UPDATE, reason=reason)
        self._sm.update_state_timestamp(part, step)

    def _reapply_layer(
        self, part: Part, layer_hash: LayerHash, *, reason: Optional[str] = None
    ):
        """Update the layer hash without changing the step state."""
        logger.debug("reapply layer %s: hash=%s", part.name, layer_hash)
        self._layer_state.set_layer_hash(part, layer_hash)
        self._add_action(
            part, Step.OVERLAY, action_type=ActionType.REAPPLY, reason=reason
        )

    def _add_action(
        self,
        part: Part,
        step: Step,
        *,
        action_type: ActionType = ActionType.RUN,
        reason: Optional[str] = None,
        project_vars: Optional[Dict[str, ProjectVar]] = None,
    ) -> None:
        logger.debug("add action %s:%s(%s)", part.name, step, action_type)
        self._actions.append(
            Action(
                part.name,
                step,
                action_type=action_type,
                reason=reason,
                project_vars=project_vars,
            )
        )

    def _ensure_overlay_consistency(
        self, top_part: Part, reason: Optional[str] = None, skip_last: bool = False
    ) -> LayerHash:
        """Make sure overlay step layers are consistent.

        The overlay step layers are stacked according to the part order. Each part
        is given an identificaton value based on its overlay parameters and the value
        of the previous layer in the stack, which is used to make sure the overlay
        parameters for all previous layers remain the same. If any previous part
        has not run, or had its parameters changed, it must run again to ensure
        overlay consistency.

        :param top_part: The part currently the top of the layer stack and whose
            consistency is to be verified.
        :param skip_last: Don't verify the consistency of the last (topmost) layer.
            This is used during the overlay stack creation.

        :return: This topmost layer's verification hash.
        """
        for part in self._part_list:
            layer_hash = self._layer_state.compute_layer_hash(part)

            # run the overlay step if the layer hash doesn't match the existing
            # state (unless we're in the top part and skipping the consistency check)
            if not (skip_last and part.name == top_part.name):
                state_layer_hash = self._layer_state.get_layer_hash(part)

                if layer_hash != state_layer_hash:
                    self._add_all_actions(
                        target_step=Step.OVERLAY,
                        part_names=[part.name],
                        reason=reason,
                    )
                    self._layer_state.set_layer_hash(part, layer_hash)

            if part.name == top_part.name:
                return layer_hash

        # execution should never reach this line
        raise RuntimeError(f"part {top_part!r} not in parts list")

    def _check_overlay_dependencies(self, part: Part, step: Step) -> bool:
        """Verify whether the step is dirty because the overlay changed."""
        if step == Step.OVERLAY:
            # Layers depend on the integrity of its validation hash
            current_layer_hash = self._layer_state.compute_layer_hash(part)
            state_layer_hash = self._layer_state.get_layer_hash(part)
            if current_layer_hash != state_layer_hash:
                logger.debug("%s:%s changed layer hash", part.name, step)
                self._reapply_layer(
                    part, current_layer_hash, reason="previous layer changed"
                )
                return True

        elif step == Step.BUILD:
            # If a part has overlay visibility, rebuild it if overlay changed
            current_overlay_hash = self._layer_state.get_overlay_hash()
            state_overlay_hash = self._sm.get_step_state_overlay_hash(part, step)

            if (
                part in self._overlay_viewers
                and current_overlay_hash != state_overlay_hash
            ):
                logger.debug("%s:%s can see overlay and it changed", part.name, step)
                self._rerun_step(part, step, reason="overlay changed")
                return True

        elif step == Step.STAGE:
            # If a part declares overlay parameters, restage it if overlay changed
            current_overlay_hash = self._layer_state.get_overlay_hash()
            state_overlay_hash = self._sm.get_step_state_overlay_hash(part, step)

            if part.has_overlay and current_overlay_hash != state_overlay_hash:
                logger.debug("%s:%s has overlay and it changed", part.name, step)
                self._rerun_step(part, step, reason="overlay changed")
                return True

        return False


_step_verb: Dict[Step, str] = {
    Step.PULL: "pull",
    Step.OVERLAY: "overlay",
    Step.BUILD: "build",
    Step.STAGE: "stage",
    Step.PRIME: "prime",
}
