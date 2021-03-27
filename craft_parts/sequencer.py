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
from typing import List, Optional

from craft_parts.actions import Action
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part, part_list_by_name, sort_parts
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
        self._actions: List[Action] = []

    def plan(self, target_step: Step, part_names: List[str] = None) -> List[Action]:
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
        part_names: List[str] = None,
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
        part_names: Optional[List[str]],
        reason: Optional[str] = None,
    ) -> None:
        # TODO: implement this stub
        pass
