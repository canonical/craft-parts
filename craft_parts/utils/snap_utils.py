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

"""Utility functions for snaps."""

import os
import shutil
from typing import Optional

import craft_parts.errors


def _find_command_path_in_root(root: str, command_name: str) -> Optional[str]:
    """Find the path of a command in a given root path."""
    for bin_directory in (
        "usr/local/sbin",
        "usr/local/bin",
        "usr/sbin",
        "usr/bin",
        "sbin",
        "bin",
    ):
        path = os.path.join(root, bin_directory, command_name)
        if os.path.exists(path):
            return path

    return None


def get_host_command(command_name: str) -> str:
    """Return the full path of the given host tool.

    :param command_name: the name of the command to resolve a path for.
    :return: Path to command

    :raises SnapcraftError: if command_name was not found.
    """
    tool = shutil.which(command_name)
    if not tool:
        raise craft_parts.errors.CommandNotFoundError(
            f"A tool craft-parts depends on could not be found: {command_name!r}",
            resolution="Ensure the tool is installed and available, and try again.",
        )
    return tool


def get_snap_command_path(command_name: str) -> str:
    """Return the path of a command found in the snap.

    If the parts is not running as a snap, shutil.which() is used
    to resolve the command using PATH.

    :param command_name: the name of the command to resolve a path for.
    :return: Path to command

    :raises CommandNotFoundError: if command_name was not found.
    """
    if not os.environ.get("SNAP_NAME"):
        return get_host_command(command_name)

    snap_path = os.getenv("SNAP")
    if snap_path is None:
        raise RuntimeError(
            "The SNAP environment variable is not defined, but SNAP_NAME is?"
        )

    command_path = _find_command_path_in_root(snap_path, command_name)

    if command_path is None:
        raise craft_parts.errors.CommandNotFoundError(
            f"Cannot find snap tool {command_name!r}",
            resolution="Please report this error to the craft-parts maintainers.",
        )

    return command_path
