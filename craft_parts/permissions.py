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
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, root_validator


class Permissions(BaseModel):
    """Description of the ownership and permission settings for a set of files.

    A ``Permissions`` object specifies that a given pattern-like ``path`` should
    be owned by ``owner`` with a given ``group``, and have the read/write/execute
    bits defined by ``mode``.

    Notes
    -----
    - ``path`` is optional and defaults to "everything";
    - ``owner`` and ``group`` are optional if both are omitted - that is, if
      one of the pair is specified then both must be;
    - ``mode`` is a string containing an integer in base 8. For example, "755",
      "0755" and "0o755" are all accepted and are the equivalent of calling
      ``chmod 755 ...``.

    """

    path: str = "*"
    owner: Optional[int] = None
    group: Optional[int] = None
    mode: Optional[str] = None

    # pylint: disable=no-self-argument
    @root_validator(pre=True)
    def validate_root(cls, values: Dict[Any, Any]) -> Dict[Any, Any]:
        """Validate that "owner" and "group" are correctly specified."""
        has_owner = "owner" in values
        has_group = "group" in values

        if has_owner != has_group:
            raise ValueError(
                'If either "owner" or "group" is defined, both must be set'
            )

        return values

    # pylint: enable=no-self-argument

    @property
    def mode_octal(self) -> int:
        """Get the mode as a base-8 integer."""
        if self.mode is None:
            raise TypeError("'mode' is not set!")
        return int(self.mode, base=8)

    def applies_to(self, path: Union[Path, str]) -> bool:
        """Whether this Permissions' path pattern applies to ``path``."""
        if self.path == "*":
            return True

        return fnmatch(str(path), self.path)

    def apply_permissions(self, target: Union[Path, str]) -> None:
        """Apply the permissions configuration to ``target``.

        Note that this method doesn't check if this ``Permissions``'s path
        pattern matches ``target``; be sure to call ``applies_to()`` beforehand.
        """
        if self.mode is not None:
            os.chmod(target, self.mode_octal)

        if self.owner is not None and self.group is not None:
            os.chown(target, self.owner, self.group)


def filter_permissions(
    target: Union[Path, str], permissions: List[Permissions]
) -> List[Permissions]:
    """Get the subset of ``permissions`` whose path patterns apply to ``target``."""
    return [p for p in permissions if p.applies_to(target)]


def apply_permissions(target: Union[Path, str], permissions: List[Permissions]) -> None:
    """Apply all permissions configurations in ``permissions`` to ``target``."""
    for permission in permissions:
        permission.apply_permissions(target)


def permissions_are_compatible(
    left: Optional[List[Permissions]], right: Optional[List[Permissions]]
) -> bool:
    """Whether two sets of permissions definitions are not in conflict with each other.

    The function determines whether applying the two lists of Permissions to a given
    path would result in the same ``owner``, ``group`` and ``mode``.

    Remarks:
    --------
    - If either of the parameters is None or empty, they are considered compatible
        because they are understood to not be "in conflict".
    - Otherwise, the permissions are incompatible if one would they would set one
        of the attributes (owner, group and mode) to different values, *even if* one
        of them would not modify the attribute at all.
    - The ``path`` attribute of the ``Permissions`` are completely ignored, as they
        are understood to apply to the same file of interest through a previous call
        of ``filter_permissions()``.

    :param left: the first set of permissions.
    :param right: the second set of permissions.
    """
    left = left or []
    right = right or []

    if len(left) == 0 or len(right) == 0:
        # If either (or both) of the lists are empty, consider them "compatible".
        return True

    # Otherwise, "squash" both lists into individual Permissions objects to
    # compare them.
    squashed_left = _squash_permissions(left)
    squashed_right = _squash_permissions(right)

    if squashed_left.owner != squashed_right.owner:
        return False

    if squashed_left.group != squashed_right.group:
        return False

    if squashed_left.mode is None and squashed_right.mode is None:
        return True

    if squashed_left.mode is None or squashed_right.mode is None:
        return False

    return squashed_left.mode_octal == squashed_right.mode_octal


def _squash_permissions(permissions: List[Permissions]) -> Permissions:
    """Compress a sequence of Permissions into a single one.

    This function produces a single ``Permissions`` object whose application to a path
    is equivalent to calling ``apply_permissions()`` with the full list ``permissions``.
    Note that the ``path`` attribute of the Permissions objects are ignored, as they
    are assumed to all match (so they must have been pre-filtered with
    ``filter_permissions``).

    :param permissions: A series of Permissions objects to be "squashed" into a single
        one.
    """
    attributes = {
        "path": "*",
        "owner": None,
        "group": None,
        "mode": None,
    }

    keys = tuple(attributes.keys())
    for permission in permissions:
        for key in keys:
            permission_value = getattr(permission, key)
            if permission_value is not None:
                attributes[key] = permission_value

    return Permissions(**attributes)
