# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2022 Canonical Ltd.
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

"""The deb source handler."""

import logging
import os
from pathlib import Path
from typing import Literal

from craft_parts.utils import deb_utils

from .base import (
    BaseFileSourceModel,
    FileSourceHandler,
    get_json_extra_schema,
    get_model_config,
)

logger = logging.getLogger(__name__)


class DebSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for deb file sources."""

    pattern = r"\.deb$"
    model_config = get_model_config(get_json_extra_schema(pattern))
    source_type: Literal["deb"] = "deb"


class DebSource(FileSourceHandler):
    """The "deb" file source handler."""

    source_model = DebSourceModel

    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Extract deb file contents to the part source dir."""
        deb_file = src if src else self.part_src_dir / os.path.basename(self.source)

        deb_utils.extract_deb(deb_file, dst, logger.debug)

        if not keep:
            deb_file.unlink()
