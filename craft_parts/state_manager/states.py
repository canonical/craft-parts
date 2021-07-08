# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""Helpers and definitions for lifecycle states."""

import contextlib
import logging
from pathlib import Path
from typing import Optional, Type

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

    :raise RuntimeError: If step is invalid.
    """
    filename = state_file_path(part, step)
    if not filename.is_file():
        return None

    logger.debug("load state file: %s", filename)
    with open(filename) as yaml_file:
        state_data = yaml.safe_load(yaml_file)

    state_class: Type[StepState]

    if step == Step.PULL:
        state_class = PullState
    elif step == Step.BUILD:
        state_class = BuildState
    elif step == Step.STAGE:
        state_class = StageState
    elif step == Step.PRIME:
        state_class = PrimeState
    else:
        raise RuntimeError(f"invalid step {step!r}")

    return state_class.unmarshal(state_data)


def remove(part: Part, step: Step) -> None:
    """Remove the persistent state file for the given part and step.

    :param part: The part whose state is to be removed.
    :param step: The step whose state is to be removed.
    """
    state_file = part.part_state_dir / step.name.lower()
    with contextlib.suppress(FileNotFoundError):  # no missing_ok in python 3.7
        state_file.unlink()


def state_file_path(part: Part, step: Step) -> Path:
    """Return the path to the state file for the give part and step."""
    return part.part_state_dir / step.name.lower()
