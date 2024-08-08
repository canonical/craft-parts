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
from typing import Any, Literal

from overrides import overrides

from craft_parts.dirs import ProjectDirs

from .base import BaseFileSourceModel, FileSourceHandler, get_model_config


class FileSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for plain file source."""

    model_config = get_model_config()
    source_type: Literal["file"]


class FileSource(FileSourceHandler):
    """The plain file source handler."""

    source_model = FileSourceModel

    def __init__(
        self,
        source: str,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        ignore_patterns: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("source_type", "file")
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            project_dirs=project_dirs,
            ignore_patterns=ignore_patterns,
            **kwargs,
        )

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Process the source file to extract its payload."""
        # No payload to extract
