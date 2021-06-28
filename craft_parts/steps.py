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

"""Definitions and helpers to handle lifecycle steps."""

import enum
from typing import List, Optional


@enum.unique
class Step(enum.IntEnum):
    """All the steps needed to fully process a part.

    Steps correspond to the tasks that must be fulfilled in order to
    process each of the parts in the project specification. In the
    ``PULL`` step sources for a part are retrieved and unpacked, and
    in the ``BUILD`` step artifacts are built and installed. In the
    ``STAGE`` step installed build artifacts from all parts are added
    to a staging area, and further processed in the ``PRIME`` step to
    obtain the final tree with files ready for deployment.
    """

    PULL = 1
    BUILD = 2
    STAGE = 3
    PRIME = 4

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def previous_steps(self) -> List["Step"]:
        """List the steps that should happen before the current step.

        :returns: The list of previous steps.
        """
        steps = []

        if self >= Step.BUILD:
            steps.append(Step.PULL)
        if self >= Step.STAGE:
            steps.append(Step.BUILD)
        if self >= Step.PRIME:
            steps.append(Step.STAGE)

        return steps

    def next_steps(self) -> List["Step"]:
        """List the steps that should happen after the current step.

        :returns: The list of next steps.
        """
        steps = []

        if self == Step.PULL:
            steps.append(Step.BUILD)
        if self <= Step.BUILD:
            steps.append(Step.STAGE)
        if self <= Step.STAGE:
            steps.append(Step.PRIME)

        return steps


def dependency_prerequisite_step(step: Step) -> Optional[Step]:
    """Obtain the step a given step may depend on.

    :returns: The prerequisite step.
    """
    #  With V2 plugins we don't need to repull if dependency is restaged
    if step == Step.PULL:
        return None

    return Step.STAGE if step <= Step.STAGE else step
