# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
from pathlib import PurePath
from typing import NamedTuple, Optional, Tuple, TypeVar, Union

from craft_parts.errors import FeatureError
from craft_parts.features import Features

FlexiblePath = TypeVar("FlexiblePath", PurePath, str)

# regex for a path beginning with a partition
HAS_PARTITION_REGEX = re.compile(r"^\([a-z]+\)(/.*)?$")

# regex for a path beginning with a namespaced partition
HAS_NAMESPACED_PARTITION_REGEX = re.compile(r"^(\([a-z]+/(?!-)[a-z\-]+(?<!-)\))(/.*)?$")


class PartitionPathPair(NamedTuple):
    """A pair containing a partition name and a path."""

    partition: Optional[str]
    path: Union[PurePath, str]


def _has_partition(path: Union[PurePath, str]) -> bool:
    """Check whether a path has an explicit partition."""
    return bool(
        HAS_PARTITION_REGEX.match(str(path))
        or HAS_NAMESPACED_PARTITION_REGEX.match(str(path))
    )


def get_partition_and_path(path: FlexiblePath) -> PartitionPathPair:
    """Break a partition path into the partition and the child path.

    If the path begins with a partition, that is used. Otherwise, the default
    partition is used.
    If partitions are not enabled, the partition will be None.

    :param path: The filepath to parse.

    :returns: A tuple of (partition, filepath)
    """
    if not Features().enable_partitions:
        return PartitionPathPair(None, path)

    str_path = str(path)

    if _has_partition(str_path):
        partition, inner_path = _split_partition_and_inner_path(str_path)
        return PartitionPathPair(partition.strip("()"), path.__class__(inner_path))

    return PartitionPathPair("default", path)


def _split_partition_and_inner_path(str_path: str) -> Tuple[str, str]:
    """Split a path with a partition into a partition and inner path.

    :param str_path: A string of the filepath beginning with a partition to split.

    :returns: A tuple containing the partition and inner path. If there is no inner
    path, the second element will be an empty string.

    :raises FeatureError: If `str_path` does not begin with a partition.
    """
    # split regular partitions
    if re.match(HAS_PARTITION_REGEX, str_path):
        if "/" in str_path:
            # split into partition and inner_path
            partition, inner_path = str_path.split("/", maxsplit=1)
            # remove extra forward slashes between the partition and inner path
            return partition, inner_path.lstrip("/")
        return str_path, ""

    # split namespaced partitions
    match = re.match(HAS_NAMESPACED_PARTITION_REGEX, str_path)

    if not match:
        raise FeatureError(f"Filepath {str_path!r} does not begin with a partition.")

    partition, inner_path = match.groups()

    # remove all forward slashes between the partition and the inner path
    inner_path = (inner_path or "").lstrip("/")

    return partition, inner_path
