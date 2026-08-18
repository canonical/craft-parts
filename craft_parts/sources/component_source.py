# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

"""The component source handler."""

import tempfile
from pathlib import Path
from typing import Literal, cast

import yaml
from typing_extensions import override

from craft_parts.utils import file_utils

from . import errors
from .base import (
    BaseFileSourceModel,
    FileSourceHandler,
    get_json_extra_schema,
    get_model_config,
)


class ComponentSourceModel(BaseFileSourceModel, frozen=True):  # type: ignore[misc]
    """Pydantic model for a component file source."""

    pattern = r"\.comp$"
    model_config = get_model_config(get_json_extra_schema(pattern))
    source_type: Literal["comp"] = "comp"


class ComponentSource(FileSourceHandler):
    """Handles downloading and extractions for a component source."""

    source_model = ComponentSourceModel

    @override
    def provision(
        self,
        dst: Path,
        keep: bool = False,
        src: Path | None = None,
    ) -> None:
        """Provision the component source.

        :param dst: The destination directory to provision to.
        :param keep: Whether to keep the component after provisioning is complete.
        :param src: Force a new source to use for extraction.

        raises errors.InvalidComponentPackage: If trying to provision an invalid component.
        """
        comp_file = src if src else self.part_src_dir / Path(self.source).name
        comp_file = comp_file.resolve()

        # unsquashfs [options] filesystem [directories or files to extract]
        # options:
        # -force: if file already exists then overwrite
        # -dest <pathname>: unsquash to <pathname>
        with tempfile.TemporaryDirectory(prefix=str(comp_file.parent)) as temp_dir:
            extract_command: list[str | Path] = [
                "unsquashfs",
                "-force",
                "-dest",
                temp_dir,
                comp_file,
            ]
            self._run_output(extract_command)
            temp_path = Path(temp_dir)
            full_comp_name = _get_full_comp_name(comp_file.name, temp_path)
            snap_name, comp_name = full_comp_name.split("+")
            comp_revision = comp_file.stem.rsplit("_", 1)[1]
            # This destination path is where snapd mounts components normally
            file_utils.link_or_copy_tree(
                source_tree=temp_path,
                destination_tree=dst
                / "snap"
                / snap_name
                / "components"
                / "mnt"
                / comp_name
                / comp_revision,
            )

        if not keep:
            comp_file.unlink()


def _get_full_comp_name(comp: str, comp_dir: Path) -> str:
    """Obtain the component name from the component details file.

    :param snap: The component package file.
    :param snap_dir: The location of the unsquashed component contents.

    :return: The component name, in the form of <parent-snap>+<component>.
    """
    try:
        with (comp_dir / "meta" / "component.yaml").open() as comp_yaml:
            return cast(str, yaml.safe_load(comp_yaml)["component"])
    except (FileNotFoundError, KeyError) as comp_error:
        raise errors.InvalidComponentPackage(comp) from comp_error
