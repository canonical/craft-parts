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

"""Support for RPM files."""

import functools
import logging
import os
import pathlib
import subprocess
from pathlib import Path
from typing import List, Sequence, Set, Tuple

from craft_parts.utils import os_utils

from . import errors
from .base import BaseRepository, get_pkg_name_parts

logger = logging.getLogger(__name__)


class RPMRepository(BaseRepository):
    """Repository management for RPM packages."""


