# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2025 Canonical Ltd.
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

"""Utility functions for paths."""

import re
from collections.abc import Iterable
from pathlib import PurePath
from typing import NamedTuple, TypeVar

from craft_parts.errors import FeatureError
from craft_parts.features import Features
from craft_parts.utils import partition_utils

FlexiblePath = TypeVar("FlexiblePath", PurePath, str)

# regex for a path beginning with a (partition), like "(boot)/bin/sh"
HAS_PARTITION_REGEX = re.compile(
    r"^(\(" + partition_utils.VALID_PARTITION_REGEX.pattern + r"\))(/.*)?$"
)

# regex for a path whose first component is any name in parentheses, like
# "(etc)/foo" or "-(etc)", regardless of whether it's a valid partition name
_PARENTHESISED_PATH_REGEX = re.compile(r"^-?\([^/]*\)(/|$)")


class PartitionPathPair(NamedTuple):
    """A pair containing a partition name and a path."""

    partition: str
    path: PurePath | str


def _has_partition(path: PurePath | str) -> bool:
    """Check whether a path has an explicit partition."""
    return bool(HAS_PARTITION_REGEX.match(str(path)))


def get_partition_and_path(
    path: FlexiblePath, default_partition: str
) -> PartitionPathPair:
    """Break a partition path into the partition and the child path.

    If the path begins with a partition, that is used. Otherwise, the default
    partition is used.
    :param path: The filepath to parse.

    :returns: A tuple of (partition, filepath)
    """
    str_path = str(path)

    if _has_partition(str_path):
        partition, inner_path = _split_partition_and_inner_path(str_path)
        return PartitionPathPair(partition.strip("()"), type(path)(inner_path))

    return PartitionPathPair(default_partition, path)


def get_user_partition_and_path(
    path: FlexiblePath,
    default_partition: str,
    *,
    special_partitions: Iterable[str] = (),
) -> PartitionPathPair:
    """Break a user-provided path into the partition and the child path.

    If the partitions feature is enabled, this is the same as
    :func:`get_partition_and_path`. Otherwise, a leading parenthesised name is
    a regular path component, unless it's one of ``special_partitions``. This
    keeps paths such as ``(etc)/foo`` working in projects without partitions.

    :param path: The filepath to parse.
    :param default_partition: The name of the default partition.
    :param special_partitions: Pseudo-partitions to parse even if partitions
        are not enabled.

    :returns: A tuple of (partition, filepath)
    """
    if Features().enable_partitions:
        return get_partition_and_path(path, default_partition)

    pair = get_partition_and_path(path, default_partition)
    if _has_partition(str(path)) and pair.partition in special_partitions:
        return pair

    return PartitionPathPair(default_partition, path)


def is_parenthesised_path(path: str) -> bool:
    """Check whether the first path component is wrapped in parentheses.

    :param path: The filepath to check, optionally prefixed with ``-``.
    """
    return bool(_PARENTHESISED_PATH_REGEX.match(path))


def _split_partition_and_inner_path(str_path: str) -> tuple[str, str]:
    """Split a path with a partition into a partition and inner path.

    :param str_path: A string of the filepath beginning with a partition to split.

    :returns: A tuple containing the partition and inner path. If there is no inner
    path, the second element will be an empty string.

    :raises FeatureError: If `str_path` does not begin with a partition.
    """
    match = re.match(HAS_PARTITION_REGEX, str_path)

    if not match:
        raise FeatureError(f"Filepath {str_path!r} does not begin with a partition.")

    partition, inner_path = match.groups()

    # remove all forward slashes between the partition and the inner path
    inner_path = (inner_path or "").lstrip("/")

    return partition, inner_path
