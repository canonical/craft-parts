# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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

"""The RPM source handler."""

import logging
import os
import subprocess
import tarfile
from pathlib import Path
from typing import Literal

from overrides import override

from . import errors
from .base import (
    BaseFileSourceModel,
    FileSourceHandler,
    get_json_extra_schema,
    get_model_config,
)

logger = logging.getLogger(__name__)


class RpmSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for an rpm file source."""

    pattern = r"\.rpm$"
    model_config = get_model_config(get_json_extra_schema(pattern))
    source_type: Literal["rpm"] = "rpm"


class RpmSource(FileSourceHandler):
    """The "rpm" file source handler."""

    source_model = RpmSourceModel

    @override
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Extract rpm file contents to the part source dir."""
        rpm_path = src or self.part_src_dir / os.path.basename(self.source)
        # NOTE: rpm2archive chosen here because while it's slower, it has broader
        # compatibility than rpm2cpio.
        # --nocompression parameter excluded until all supported platforms
        # include rpm >= 4.17
        command = ["rpm2archive", "-"]

        with rpm_path.open("rb") as rpm:
            try:
                with subprocess.Popen(
                    command, stdin=rpm, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ) as archive:
                    with tarfile.open(mode="r|*", fileobj=archive.stdout) as tar:
                        tar.extractall(path=dst)
            except (tarfile.TarError, subprocess.CalledProcessError) as err:
                raise errors.InvalidRpmPackage(rpm_path.name) from err

        if not keep:
            rpm_path.unlink()
