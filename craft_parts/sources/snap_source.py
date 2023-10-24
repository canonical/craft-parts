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

import shutil
import tempfile
from pathlib import Path
from typing import cast

import yaml
from overrides import overrides

from craft_parts.dirs import ProjectDirs
from craft_parts.utils import file_utils

from . import errors
from .base import FileSourceHandler


class SnapSource(FileSourceHandler):
    """Handles downloading and extractions for a snap source.

    On provision, the meta directory is renamed to meta.<snap-name> and, if present,
    the same applies for the snap directory which shall be renamed to
    snap.<snap-name>.
    """

    def __init__(  # noqa: PLR0913
        self,
        source: Path,
        part_src_dir: Path,
        *,
        cache_dir: Path,
        project_dirs: ProjectDirs,
        source_tag: str | None = None,
        source_commit: str | None = None,
        source_branch: str | None = None,
        source_depth: int | None = None,
        source_checksum: str | None = None,
        **kwargs,  # noqa: ANN003
    ) -> None:
        super().__init__(
            source,
            part_src_dir,
            cache_dir=cache_dir,
            source_tag=source_tag,
            source_commit=source_commit,
            source_branch=source_branch,
            source_depth=source_depth,
            source_checksum=source_checksum,
            project_dirs=project_dirs,
            command="unsquashfs",
            **kwargs,
        )

        if source_tag:
            raise errors.InvalidSourceOption(source_type="snap", option="source-tag")

        if source_commit:
            raise errors.InvalidSourceOption(source_type="snap", option="source-commit")

        if source_branch:
            raise errors.InvalidSourceOption(source_type="snap", option="source-branch")

        if source_depth:
            raise errors.InvalidSourceOption(source_type="snap", option="source-depth")

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
        if not isinstance(self.source, Path):
            raise errors.InvalidSnapPackage(str(self.source))
        snap_file = src if src else self.part_src_dir / self.source.name
        snap_file = snap_file.resolve()

        # unsquashfs [options] filesystem [directories or files to extract]
        # options:
        # -force: if file already exists then overwrite
        # -dest <pathname>: unsquash to <pathname>
        with tempfile.TemporaryDirectory(prefix=str(snap_file.parent)) as _temp_dir:
            temp_dir = Path(_temp_dir)
            extract_command: list[str] = [
                "unsquashfs",
                "-force",
                "-dest",
                _temp_dir,
                str(snap_file),
            ]
            self._run_output(extract_command)
            snap_name = _get_snap_name(snap_file.name, _temp_dir)
            # Rename meta and snap dirs from the snap
            rename_paths = (temp_dir / d for d in ["meta", "snap"])
            rename_paths = (d for d in rename_paths if d.exists())
            for rename in rename_paths:
                shutil.move(rename, f"{rename}.{snap_name}")
            file_utils.link_or_copy_tree(source_tree=temp_dir, destination_tree=dst)

        if not keep:
            snap_file.unlink()


def _get_snap_name(snap: str, snap_dir: str) -> str:
    """Obtain the snap name from the snap details file.

    :param snap: The snap package file.
    :param snap_dir: The location of the unsquashed snap contents.

    :return: The snap name.
    """
    try:
        with Path(snap_dir, "meta", "snap.yaml").open() as snap_yaml:
            return cast(str, yaml.safe_load(snap_yaml)["name"])
    except (FileNotFoundError, KeyError) as snap_error:
        raise errors.InvalidSnapPackage(snap) from snap_error
