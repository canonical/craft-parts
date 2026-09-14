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

"""Support for Chisel operations."""

import logging
import pathlib
import subprocess
from io import StringIO
from typing import Any

import yaml
from pydantic import BaseModel

from craft_parts.packages import errors
from craft_parts.packages.base import logger
from craft_parts.utils import os_utils


class SlicesState(BaseModel):
    """State for cut slices."""

    slices: set[str] = set()

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "SlicesState":
        """Create and populate a new state object from dictionary data.

        :param data: A dictionary containing the data to unmarshal.

        :returns: The state object containing the slice data.
        """
        return cls.model_validate(data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the part state data.

        :return: The newly created dictionary.
        """
        return self.model_dump(by_alias=True)

    def write(self, filepath: pathlib.Path) -> None:
        """Write state data to disk.

        :param filepath: The path to the file to write.
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        yaml_data = yaml.safe_dump(self.model_dump())
        os_utils.TimedWriter.write_text(filepath, yaml_data)

    @classmethod
    def read(cls, filepath: pathlib.Path) -> "SlicesState":
        """Read state data from disk.

        :param filepath: The path to the file to read.

        :returns: The state object containing the slice data.
        """
        yaml_data = filepath.read_text()
        data = yaml.safe_load(yaml_data)
        return cls.unmarshal(data)


def cut_slices(slices: list[str], target_dir: pathlib.Path) -> None:
    """Cut Chisel slices into a destination path.

    :param slices: The list of names of slices to cut.
    :param target_dir: The destination directory.
    """
    output_stream = StringIO()
    handler = logging.StreamHandler(stream=output_stream)
    logger.addHandler(handler)
    try:
        os_utils.process_run(
            [
                "chisel",
                "cut",
                "--ignore=unmaintained",
                "--ignore=unstable",
                f"--root={target_dir}",
                *slices,
            ],
            logger.debug,
        )
    except subprocess.CalledProcessError as err:
        command_output = output_stream.getvalue()
        raise errors.ChiselError(slices=slices, output=command_output) from err
    finally:
        logger.removeHandler(handler)
        handler.close()
