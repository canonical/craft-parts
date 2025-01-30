# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

from . import plugins
from .actions import Action, ActionProperties, ActionType
from .dirs import ProjectDirs
from .errors import PartsError
from .executor import expand_environment
from .features import Features
from .infos import PartInfo, ProjectInfo, StepInfo
from .lifecycle_manager import LifecycleManager
from .parts import (
    Part,
    part_has_chisel_as_build_snap,
    part_has_slices,
    part_has_overlay,
    validate_part,
)
from .steps import Step


try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("craft_parts")
    except PackageNotFoundError:
        __version__ = "dev"


__all__ = [
    "__version__",
    "Features",
    "Action",
    "ActionProperties",
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
    "part_has_overlay",
    "part_has_slices",
    "part_has_chisel_as_build_snap",
]
