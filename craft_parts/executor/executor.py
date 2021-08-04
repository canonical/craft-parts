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

"""Definitions and helpers for the action executor."""

import contextlib
import logging
import shutil
from typing import Dict, List, Union

from craft_parts import callbacks, packages, parts
from craft_parts.actions import Action, ActionType
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .collisions import check_for_stage_collisions
from .part_handler import PartHandler

logger = logging.getLogger(__name__)


class Executor:
    """Execute lifecycle actions.

    The executor takes the part definition and a list of actions to run for
    a part and step. Action execution is stateless: no information is kept from
    the execution of previous parts. On-disk state information written after
    running each action is read by the sequencer before planning a new set of
    actions.

    :param part_list: The list of parts to process.
    :param project_info: Information about this project.
    :param extra_build_packages: Additional packages to install on the host system.
    :param extra_build_snaps: Additional snaps to install on the host system.
    :param ignore_patterns: File patterns to ignore when pulling local sources.
    """

    def __init__(
        self,
        *,
        part_list: List[Part],
        project_info: ProjectInfo,
        extra_build_packages: List[str] = None,
        extra_build_snaps: List[str] = None,
        ignore_patterns: List[str] = None,
    ):
        self._part_list = part_list
        self._project_info = project_info
        self._extra_build_packages = extra_build_packages
        self._extra_build_snaps = extra_build_snaps
        self._handler: Dict[str, PartHandler] = {}
        self._ignore_patterns = ignore_patterns

    def prologue(self) -> None:
        """Prepare the execution environment.

        This method is called before executing lifecycle actions.
        """
        self._install_build_packages()
        self._install_build_snaps()

        callbacks.run_prologue(self._project_info, part_list=self._part_list)

    def epilogue(self) -> None:
        """Finish and clean the execution environment.

        This method is called after executing lifecycle actions.
        """
        callbacks.run_epilogue(self._project_info, part_list=self._part_list)

    def execute(self, actions: Union[Action, List[Action]]) -> None:
        """Execute the specified action or list of actions.

        :param actions: An :class:`Action` object or list of :class:`Action`
           objects specifying steps to execute.

        :raises InvalidActionException: If the action parameters are invalid.
        """
        if isinstance(actions, Action):
            actions = [actions]

        for act in actions:
            self._run_action(act)

    def clean(self, initial_step: Step, *, part_names: List[str] = None) -> None:
        """Clean the given parts, or all parts if none is specified.

        :param initial_step: The step to clean. More steps may be cleaned
            as a consequence of cleaning the initial step.
        :param part_names: A list with names of the parts to clean. If not
            specified, all parts will be cleaned and work directories
            will be removed.
        """
        selected_parts = parts.part_list_by_name(part_names, self._part_list)

        selected_steps = [initial_step] + initial_step.next_steps()
        selected_steps.reverse()

        for part in selected_parts:
            handler = self._create_part_handler(part)

            for step in selected_steps:
                handler.clean_step(step=step)

        if not part_names:
            # also remove toplevel directories if part names are not specified
            with contextlib.suppress(FileNotFoundError):
                shutil.rmtree(self._project_info.prime_dir)
                if initial_step <= Step.STAGE:
                    shutil.rmtree(self._project_info.stage_dir)
                if initial_step <= Step.PULL:
                    shutil.rmtree(self._project_info.parts_dir)

    def _run_action(self, action: Action) -> None:
        """Execute the given action for a part using the provided step information.

        :param action: The lifecycle action to run.
        """
        part = parts.part_by_name(action.part_name, self._part_list)

        logger.debug("execute action %s:%s", part.name, action)

        if action.action_type == ActionType.SKIP:
            logger.debug("Skip execution of %s (because %s)", action, action.reason)
            return

        if action.step == Step.STAGE:
            check_for_stage_collisions(self._part_list)

        handler = self._create_part_handler(part)
        handler.run_action(action)

    def _create_part_handler(self, part: Part) -> PartHandler:
        """Instantiate a part handler for a new part."""
        if part.name in self._handler:
            return self._handler[part.name]

        handler = PartHandler(
            part,
            part_info=PartInfo(self._project_info, part),
            part_list=self._part_list,
            ignore_patterns=self._ignore_patterns,
        )
        self._handler[part.name] = handler

        return handler

    def _install_build_packages(self) -> None:
        for part in self._part_list:
            self._create_part_handler(part)

        build_packages = set()
        for handler in self._handler.values():
            build_packages.update(handler.build_packages)

        if self._extra_build_packages:
            build_packages.update(self._extra_build_packages)

        packages.Repository.install_build_packages(sorted(build_packages))

    def _install_build_snaps(self) -> None:
        build_snaps = set()
        for handler in self._handler.values():
            build_snaps.update(handler.build_snaps)

        if self._extra_build_snaps:
            build_snaps.update(self._extra_build_snaps)

        if not build_snaps:
            return

        if os_utils.is_inside_container():
            logger.warning(
                (
                    "The following snaps are required but not installed as the "
                    "application is running inside docker or podman container: %s.\n"
                    "Please ensure the environment is properly setup before "
                    "continuing.\nIgnore this message if the appropriate measures "
                    "have already been taken.",
                    ", ".join(build_snaps),
                )
            )
        else:
            packages.snaps.install_snaps(build_snaps)


class ExecutionContext:
    """A context manager to handle lifecycle action executions."""

    def __init__(
        self,
        *,
        executor: Executor,
    ):
        self._executor = executor

    def __enter__(self) -> "ExecutionContext":
        self._executor.prologue()
        return self

    def __exit__(self, *exc):
        self._executor.epilogue()

    def execute(self, actions: Union[Action, List[Action]]) -> None:
        """Execute the specified action or list of actions.

        :param actions: An :class:`Action` object or list of :class:`Action`
           objects specifying steps to execute.

        :raises InvalidActionException: If the action parameters are invalid.
        """
        self._executor.execute(actions)
