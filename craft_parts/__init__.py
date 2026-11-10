# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

import importlib.metadata

# The Rust extension is required. Import it first so a contributor who hasn't
# built it gets an actionable error instead of a raw ModuleNotFoundError when a
# submodule pulls it in.
try:
    from . import _rs as _rs
except ImportError as exc:
    raise ImportError(
        "craft-parts requires its compiled Rust extension, which failed to "
        "import. If you are working from a source checkout, build it with "
        "'make develop' (uv run maturin develop --uv)."
    ) from exc

from . import plugins
from .actions import Action, ActionProperties, ActionType
from .dirs import ProjectDirs
from .errors import PartsError
from .executor import expand_environment
from .features import Features
from .infos import PartInfo, ProjectInfo, ProjectVar, ProjectVarInfo, StepInfo
from .lifecycle_manager import LifecycleManager
from .parts import (
    Part,
    part_has_chisel_as_build_snap,
    part_has_slices,
    part_has_overlay,
    validate_part,
)
from .steps import Step

# Read the version from the installed package metadata so it always matches
# what pip reports verbatim.
__version__ = importlib.metadata.version("craft-parts")


__all__ = [
    "__version__",
    "Features",
    "Action",
    "ActionProperties",
    "ActionType",
    "PartInfo",
    "PartsError",
    "ProjectDirs",
    "ProjectInfo",
    "ProjectVar",
    "ProjectVarInfo",
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
