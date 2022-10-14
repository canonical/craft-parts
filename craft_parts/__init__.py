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

"""Craft a project from several parts."""

__version__ = "1.15.1"

from . import plugins
from .actions import Action, ActionType
from .dirs import ProjectDirs
from .errors import PartsError
from .executor.environment import expand_environment
from .infos import PartInfo, ProjectInfo, StepInfo
from .lifecycle_manager import LifecycleManager
from .parts import Part, validate_part
from .steps import Step

__all__ = [
    "Action",
    "ActionType",
    "ProjectDirs",
    "PartsError",
    "ProjectInfo",
    "PartInfo",
    "StepInfo",
    "LifecycleManager",
    "Part",
    "Step",
    "plugins",
    "expand_environment",
    "validate_part",
]
