# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""Helpers to cut Chisel slices for the build environment."""

import logging
import subprocess
from io import StringIO
from pathlib import Path

from craft_parts.utils import os_utils

from . import errors

logger = logging.getLogger(__name__)


def is_slice(name: str) -> bool:
    """Return whether ``name`` uses the Chisel slice syntax.

    A slice is referenced as ``<package-name>_<slice-name>``. This only checks the
    format of the name; it does not verify that the slice exists.

    :param name: The name to check.
    """
    return "_" in name


def validate_slices(slices: list[str]) -> None:
    """Ensure that every entry in ``slices`` is a valid Chisel slice reference.

    :param slices: The list of slice names to validate.

    :raises InvalidBuildSlices: If any entry is not a valid Chisel slice.
    """
    invalid = [name for name in slices if not is_slice(name)]
    if invalid:
        raise errors.InvalidBuildSlices(invalid)


def cut_slices(slices: list[str], *, root: Path) -> None:
    """Cut the given Chisel slices into ``root``.

    The Chisel release and architecture are auto-detected by ``chisel`` from the
    build environment, which matches the project's base.

    :param slices: The list of slice names to cut.
    :param root: The destination directory for the cut slices.

    :raises InvalidBuildSlices: If any entry is not a valid Chisel slice.
    :raises ChiselError: If the ``chisel`` command fails.
    """
    if not slices:
        return

    validate_slices(slices)

    root.mkdir(parents=True, exist_ok=True)

    command = [
        "chisel",
        "cut",
        "--ignore=unmaintained",
        "--ignore=unstable",
        f"--root={root}",
        *slices,
    ]

    logger.debug("Cutting build slices: %s", ", ".join(slices))

    # Capture the command output so it can be reported if the command fails.
    output_stream = StringIO()
    handler = logging.StreamHandler(stream=output_stream)
    logger.addHandler(handler)
    try:
        os_utils.process_run(command, logger.debug)
    except subprocess.CalledProcessError as err:
        raise errors.ChiselError(
            slices=slices, output=output_stream.getvalue()
        ) from err
    finally:
        logger.removeHandler(handler)
