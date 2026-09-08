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

from craft_parts.packages import errors
from craft_parts.packages.base import logger
from craft_parts.utils import os_utils


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
