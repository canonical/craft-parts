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

__version__ = "1.1.0"  # noqa: F401

from .actions import Action, ActionType  # noqa: F401
from .dirs import ProjectDirs  # noqa: F401
from .errors import PartsError  # noqa: F401
from .infos import PartInfo, ProjectInfo, StepInfo  # noqa: F401
from .lifecycle_manager import LifecycleManager  # noqa: F401
from .parts import Part  # noqa: F401
from .steps import Step  # noqa: F401

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
]
