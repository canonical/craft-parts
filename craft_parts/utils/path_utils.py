# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
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

"""Utility functions for paths."""
import re
from pathlib import PurePath, PurePosixPath
from typing import NamedTuple, Optional, TypeVar, Union, cast

from craft_parts.features import Features

FlexiblePath = TypeVar("FlexiblePath", PurePath, str)

HAS_PARTITION_REGEX = re.compile(r"^\([a-z]+\)(/.*)?$")


class PartitionPathPair(NamedTuple):
    """A pair containing a partition name and a path."""

    partition: Optional[str]
    path: Union[PurePath, str]


def _has_partition(path: Union[PurePath, str]) -> bool:
    """Check whether a path has an explicit partition."""
    return bool(HAS_PARTITION_REGEX.match(str(path)))


def get_partitioned_path(path: FlexiblePath) -> FlexiblePath:
    """Get a filepath compatible with the partitions feature.

    If the filepath begins with a partition, then the parentheses are stripped from the
    the partition. For example, `(default)/file` is converted to `default/file`.

    If the filepath does not begin with a partition, the `default` partition is
    prepended. For example, `file` is converted to `default/file`.

    :param path: The filepath to modify.

    :returns: A filepath that is compatible with the partitions feature.
    """
    if not Features().enable_partitions:
        return path

    if str(path) == "*":
        return path

    partition, inner_path = get_partition_and_path(path)

    new_filepath = PurePosixPath(partition or ".", str(inner_path))
    return path.__class__(new_filepath)


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
        if "/" not in str_path:
            return PartitionPathPair(str_path.strip("()"), cast(FlexiblePath, ""))
        partition, inner_path = str_path.split("/", maxsplit=1)
        return PartitionPathPair(partition.strip("()"), path.__class__(inner_path))
    return PartitionPathPair("default", path)
