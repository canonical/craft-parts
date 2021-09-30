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
    ``PULL`` step sources for a part are retrieved and unpacked. The
    ``OVERLAY`` step is used to change the underlying filesystem.
    In the ``BUILD`` step artifacts are built and installed. In the
    ``STAGE`` step installed build artifacts from all parts and
    overlay contents are added to a staging area. These files are
    further processed in the ``PRIME`` step to obtain the final tree
    with the final payload for deployment.
    """

    PULL = 1
    OVERLAY = 2
    BUILD = 3
    STAGE = 4
    PRIME = 5

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def previous_steps(self) -> List["Step"]:
        """List the steps that should happen before the current step.

        :returns: The list of previous steps.
        """
        steps = []

        if self >= Step.OVERLAY:
            steps.append(Step.PULL)
        if self >= Step.BUILD:
            steps.append(Step.OVERLAY)
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
            steps.append(Step.OVERLAY)
        if self <= Step.OVERLAY:
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
    if step <= Step.OVERLAY:
        return None

    if step <= Step.STAGE:
        return Step.STAGE

    return step
