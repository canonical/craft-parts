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

"""deb-related utilities used by both `packages` and `sources`."""

import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

from craft_parts import errors
from craft_parts.utils import os_utils


def extract_deb(
    deb_path: Path, extract_dir: Path, log_func: Callable[[str], None]
) -> None:
    """Extract file `deb_path` into `extract_dir`."""
    command = ["dpkg-deb", "--extract", str(deb_path), str(extract_dir)]
    try:
        os_utils.process_run(
            command=command,
            log_func=log_func,
        )
    except subprocess.CalledProcessError as err:
        raise errors.DebError(deb_path, command, err.returncode) from err


def _is_chisel_slice(name: str) -> bool:
    """Return whether a name is a Deb package or a Chisel slice.

    A Chisel slice uses the `<package-name>_<slice-name>` syntax.

    This is a simple check that assumes the name is either a valid Deb package
    or Chisel slice.

    :param name: A package or slice name.
    """
    return "_" in name


def has_slices(names: Iterable[str]) -> bool:
    """Return whether a list contains any Chisel slices.

    :param names: An iterable of packages and slices.
    """
    return any(_is_chisel_slice(name) for name in names)


def has_debs(names: Iterable[str]) -> bool:
    """Return whether a list contains any Debian packages.

    :param names: An iterable of packages and slices.
    """
    return any(not _is_chisel_slice(name) for name in names)
