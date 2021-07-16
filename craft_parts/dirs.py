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

"""Definitions for project directories."""

from pathlib import Path
from typing import Union


class ProjectDirs:
    """The project's main work directories.

    :param work_dir: The parent directory containing the parts, prime and stage
        subdirectories. If not specified, the current directory will be used.
    """

    def __init__(self, *, work_dir: Union[Path, str] = "."):
        self._work_dir = Path(work_dir).expanduser().resolve()

    @property
    def work_dir(self) -> Path:
        """Return the root of the work directories used for project processing."""
        return self._work_dir

    @property
    def parts_dir(self) -> Path:
        """Return the directory containing work subdirectories for each part."""
        return self._work_dir / "parts"

    @property
    def stage_dir(self) -> Path:
        """Return the staging area containing installed files from all parts."""
        return self._work_dir / "stage"

    @property
    def prime_dir(self) -> Path:
        """Return the primed tree containing the final artifacts to deploy."""
        return self._work_dir / "prime"
