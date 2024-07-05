# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""Implement the plain file source handler."""

from pathlib import Path
from typing import Literal

from overrides import overrides

from craft_parts.dirs import ProjectDirs

from . import errors
from .base import FileSourceHandler, get_model_config
from .base import FileSourceModel as BaseFileSourceModel


class FileSourceModel(BaseFileSourceModel, frozen=True):
    model_config = get_model_config()
    source_type: Literal["file"] = "file"


class FileSource(FileSourceHandler):
    """The plain file source handler."""

    source_model = FileSourceModel

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Process the source file to extract its payload."""
        # No payload to extract
