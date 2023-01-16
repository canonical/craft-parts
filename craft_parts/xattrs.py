# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2019-2023 Canonical Ltd.
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

"""Helpers to read and write filesystem extended attributes."""

import logging
import os
import sys
from typing import Optional

from craft_parts import errors

logger = logging.getLogger(__name__)


def read_xattr(path: str, key: str) -> Optional[str]:
    """Get extended attribute metadata from a file.

    :param path: The file to get metadata from.
    :param key: The attribute key.

    :return: The attribute value.
    """
    if sys.platform != "linux":
        raise RuntimeError("xattr support only available for Linux")

    # Extended attributes do not apply to symlinks.
    if os.path.islink(path):
        return None

    key = f"user.craft_parts.{key}"

    try:
        value = os.getxattr(path, key)
    except OSError as error:
        # No label present with:
        # OSError: [Errno 61] No data available: b'<path>'
        if error.errno == 61:
            return None

        # Chain unknown variants of OSError.
        raise errors.XAttributeError(key=key, path=path) from error

    return value.decode().strip()


def write_xattr(path: str, key: str, value: str) -> None:
    """Add extended attribute metadata to a file.

    :param path: The file to add metadata to.
    :param key: The attribute key.
    :param value: The attribute value.
    """
    if sys.platform != "linux":
        raise RuntimeError("xattr support only available for Linux")

    # Extended attributes do not apply to symlinks.
    if os.path.islink(path):
        return

    key = f"user.craft_parts.{key}"

    try:
        os.setxattr(path, key, value.encode())
    except OSError as error:
        # Label is too long for filesystem:
        # OSError: [Errno 7] Argument list too long: b'<path>'
        if error.errno == 7:
            raise errors.XAttributeTooLong(path=path, key=key, value=value)

        # Chain unknown variants of OSError.
        raise errors.XAttributeError(key=key, path=path, is_write=True) from error
