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

"""Definitions of lifecycle actions and action types."""

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

from craft_parts.steps import Step

if TYPE_CHECKING:
    from craft_parts.infos import ProjectVar


@enum.unique
class ActionType(enum.IntEnum):
    """The type of action to be executed.

    Action execution can be modified according to its type:

    ``RUN``: execute the expected commands for step processing.

    ``RERUN``: clear the existing data and state before procceeding.

    ``UPDATE``: try to continue processing the step.

    ``SKIP``: don't execute this action.

    ``REAPPLY``: run the step commands without updating its state.
    """

    RUN = 0
    RERUN = 1
    SKIP = 2
    UPDATE = 3
    REAPPLY = 4

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


@dataclass(frozen=True)
class Action:
    """The action to be executed for a given part.

    Actions correspond to the operations required to run the lifecycle
    for each of the parts in the project specification.

    :param part_name: The name of the part this action will be
        performed on.
    :param step: The :class:`Step` this action will execute.
    :param action_type: Action to run for this step.
    :param reason: A textual description of why this action should be
        executed.
    :param project_vars: The values of project variables from a previous
        execution, used if the action type is ``ActionType.SKIP``.
    """

    part_name: str
    step: Step
    action_type: ActionType = ActionType.RUN
    reason: Optional[str] = None
    project_vars: Optional[Dict[str, "ProjectVar"]] = None
