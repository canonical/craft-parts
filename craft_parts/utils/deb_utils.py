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
from pathlib import Path
from typing import Callable

from craft_parts import errors
from craft_parts.utils import os_utils


def extract_deb(
    deb_path: Path, extract_dir: Path, log_func: Callable[[str], None]
) -> None:
    """Extract file `deb_path` into `extract_dir."""
    command = ["dpkg-deb", "--extract", str(deb_path), str(extract_dir)]
    try:
        os_utils.process_run(
            command=command,
            log_func=log_func,
        )
    except subprocess.CalledProcessError as err:
        raise errors.DebError(deb_path, command, err.returncode) from err
