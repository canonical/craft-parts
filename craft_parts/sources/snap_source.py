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

"""The snap source handler."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal, cast

import yaml
from overrides import overrides

from craft_parts.utils import file_utils

from . import errors
from .base import (
    BaseFileSourceModel,
    FileSourceHandler,
    get_json_extra_schema,
    get_model_config,
)


class SnapSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for a snap file source."""

    pattern = r"\.snap$"
    model_config = get_model_config(get_json_extra_schema(pattern))
    source_type: Literal["snap"] = "snap"


class SnapSource(FileSourceHandler):
    """Handles downloading and extractions for a snap source.

    On provision, the meta directory is renamed to meta.<snap-name> and, if present,
    the same applies for the snap directory which shall be renamed to
    snap.<snap-name>.
    """

    source_model = SnapSourceModel

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Provision the snap source.

        :param dst: The destination directory to provision to.
        :param keep: Whether to keep the snap after provisioning is complete.
        :param src: Force a new source to use for extraction.

        raises errors.InvalidSnap: If trying to provision an invalid snap.
        """
        snap_file = src if src else self.part_src_dir / os.path.basename(self.source)
        snap_file = snap_file.resolve()

        # unsquashfs [options] filesystem [directories or files to extract]
        # options:
        # -force: if file already exists then overwrite
        # -dest <pathname>: unsquash to <pathname>
        with tempfile.TemporaryDirectory(prefix=str(snap_file.parent)) as temp_dir:
            extract_command = [
                "unsquashfs",
                "-force",
                "-dest",
                temp_dir,
                snap_file,
            ]
            self._run_output(extract_command)
            snap_name = _get_snap_name(snap_file.name, temp_dir)
            # Rename meta and snap dirs from the snap
            rename_paths = (os.path.join(temp_dir, d) for d in ["meta", "snap"])
            rename_paths = (d for d in rename_paths if os.path.exists(d))
            for rename in rename_paths:
                shutil.move(rename, f"{rename}.{snap_name}")
            file_utils.link_or_copy_tree(
                source_tree=temp_dir, destination_tree=str(dst)
            )

        if not keep:
            os.remove(snap_file)


def _get_snap_name(snap: str, snap_dir: str) -> str:
    """Obtain the snap name from the snap details file.

    :param snap: The snap package file.
    :param snap_dir: The location of the unsquashed snap contents.

    :return: The snap name.
    """
    try:
        with open(os.path.join(snap_dir, "meta", "snap.yaml")) as snap_yaml:
            return cast(str, yaml.safe_load(snap_yaml)["name"])
    except (FileNotFoundError, KeyError) as snap_error:
        raise errors.InvalidSnapPackage(snap) from snap_error
