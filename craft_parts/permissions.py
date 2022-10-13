# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""Specify and apply permissions and ownership to part-owned files."""

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, root_validator


class Permissions(BaseModel):
    """Description of the ownership and permission settings for a set of files.

    A `Permissions` object specifies that a given pattern-like `path` should
    be owned by `owner` with a given `group`, and have the read/write/execute
    bits defined by `mode`.

    Notes
    -----
      - `path` is optional and defaults to "everything";
      - `owner` and `group` are optional if both are omitted - that is, if
        one of the pair is specified then both must be;
      - `mode` is a string containing an integer in base 8. For example, "755",
      "0755" and "0o755" are all accepted and are the equivalent of calling
      `chmod 755 ...`.

    """

    path: str = "*"
    owner: Optional[int] = None
    group: Optional[int] = None
    mode: Optional[str] = None

    # pylint: disable=no-self-argument
    @root_validator(pre=True)
    def validate_root(cls, values):
        """Validate that "owner" and "group" are correctly specified."""
        has_owner = "owner" in values
        has_group = "group" in values

        assert (
            has_group == has_owner
        ), 'If either "owner" or "group" is defined, both must be'

        return values

    # pylint: enable=no-self-argument

    @property
    def mode_octal(self) -> int:
        """Get the mode as a base-8 integer."""
        if self.mode is None:
            raise TypeError("'mode' is not set!")
        return int(self.mode, base=8)

    def applies_to(self, path: Union[Path, str]) -> bool:
        """Whether this Permissions' path pattern applies to `path`."""
        if self.path == "*":
            return True

        return fnmatch(str(path), self.path)

    def apply_permissions(self, target: Union[Path, str]) -> None:
        """Apply the permissions configuration to `target`.

        Note that this method doesn't check if this `Permissions`'s path
        pattern matches `target`; be sure to call `applies_to()` beforehand.
        """
        if self.mode is not None:
            os.chmod(target, self.mode_octal)

        if self.owner is not None and self.group is not None:
            os.chown(target, self.owner, self.group)


def filter_permissions(
    target: Union[Path, str], permissions: List[Permissions]
) -> List[Permissions]:
    """Get the subset of `permissions` whose path patterns apply to `target`."""
    return [p for p in permissions if p.applies_to(target)]


def apply_permissions(target: Union[Path, str], permissions: List[Permissions]) -> None:
    """Apply all permissions configurations in `permissions` to `target`."""
    for permission in permissions:
        permission.apply_permissions(target)
