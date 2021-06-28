# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2019-2021 Canonical Ltd.
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

import os
import sys
from typing import Optional

from craft_parts import errors

# TODO: this might be a separations of concern leak, improve this handling.
_STAGE_PACKAGE_KEY = "origin_stage_package"


def _get_xattr_key(key: str) -> str:
    return f"user.craft_parts.{key}"


def _read_xattr(path: str, key: str) -> Optional[str]:
    if sys.platform != "linux":
        raise RuntimeError("xattr support only available for Linux")

    # Extended attributes do not apply to symlinks.
    if os.path.islink(path):
        return None

    key = _get_xattr_key(key)
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


def _write_xattr(path: str, key: str, value: str) -> None:
    if sys.platform != "linux":
        raise RuntimeError("xattr support only available for Linux")

    # Extended attributes do not apply to symlinks.
    if os.path.islink(path):
        return

    key = _get_xattr_key(key)

    try:
        os.setxattr(path, key, value.encode())
    except OSError as error:
        # Label is too long for filesystem:
        # OSError: [Errno 7] Argument list too long: b'<path>'
        if error.errno == 7:
            raise errors.XAttributeTooLong(path=path, key=key, value=value)

        # Chain unknown variants of OSError.
        raise errors.XAttributeError(key=key, path=path, is_write=True) from error


def read_origin_stage_package(path: str) -> Optional[str]:
    """Read origin stage package."""
    return _read_xattr(path, _STAGE_PACKAGE_KEY)


def write_origin_stage_package(path: str, value: str) -> None:
    """Write origin stage package."""
    _write_xattr(path, _STAGE_PACKAGE_KEY, value)
