# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017 Tim Süberkrüb
# Copyright 2018-2022 Canonical Ltd.
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

"""Implement the 7zip file source handler."""

import os
from pathlib import Path
from typing import Literal

from .base import (
    BaseFileSourceModel,
    FileSourceHandler,
    get_json_extra_schema,
    get_model_config,
)


class SevenzipSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic for a 7zip file source."""

    pattern = r"\.7z$"
    model_config = get_model_config(get_json_extra_schema(pattern))
    source_type: Literal["7z"] = "7z"


class SevenzipSource(FileSourceHandler):
    """The zip file source handler."""

    source_model = SevenzipSourceModel

    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Extract 7z file contents to the part source dir."""
        if src:
            sevenzip_file = src
        else:
            sevenzip_file = Path(self.part_src_dir, os.path.basename(self.source))

        sevenzip_file = sevenzip_file.expanduser().resolve()
        self._run_output(["7z", "x", f"-o{dst}", str(sevenzip_file)])

        if not keep:
            os.remove(sevenzip_file)
