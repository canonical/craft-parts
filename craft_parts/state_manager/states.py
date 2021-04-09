# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""Helpers and definitions for lifecycle states."""

import logging
from pathlib import Path
from typing import Optional

import yaml

from craft_parts.parts import Part
from craft_parts.steps import Step

from .build_state import BuildState
from .prime_state import PrimeState
from .pull_state import PullState
from .stage_state import StageState
from .step_state import StepState

logger = logging.getLogger(__name__)


def load_state(part: Part, step: Step) -> Optional[StepState]:
    """Retrieve the persistent state for the given part and step.

    :param part: The part corresponding to the state to load.
    :param step: The step corresponding to the state to load.

    :return: The step state.
    """
    filename = state_file_path(part, step)
    if not filename.is_file():
        return None

    logger.debug("load state file: %s", filename)
    with open(filename) as f:
        state_data = yaml.safe_load(f)

    if step == Step.PULL:
        state_class = PullState
    elif step == Step.BUILD:
        state_class = BuildState
    elif step == Step.STAGE:
        state_class = StageState
    else:
        state_class = PrimeState

    return state_class.unmarshal(state_data)


def state_file_path(part: Part, step: Step) -> Path:
    """Return the path to the state file for the give part and step."""
    return part.part_state_dir / step.name.lower()
