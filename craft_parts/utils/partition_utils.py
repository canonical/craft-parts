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

"""Partition helpers."""

import re
from pathlib import PurePath, PurePosixPath
from typing import TypeVar, Union

from craft_parts.features import Features

FlexiblePath = TypeVar("FlexiblePath", bound=Union[PurePath, str])


HAS_PARTITION_REGEX = re.compile(r"^\([a-z]+\)(/.*)?$")


def _has_partition(path: FlexiblePath) -> bool:
    """Check whether a path has an explicit partition."""
    return bool(HAS_PARTITION_REGEX.match(str(path)))


def get_partition_compatible_filepath(filepath: FlexiblePath) -> FlexiblePath:
    """Get a filepath compatible with the partitions feature.

    If the filepath begins with a partition, then the parentheses are stripped from the
    the partition. For example, `(default)/file` is converted to `default/file`.

    If the filepath does not begin with a partition, the `default` partition is
    prepended. For example, `file` is converted to `default/file`.

    :param filepath: The filepath to modify.

    :returns: A filepath that is compatible with the partitions feature.
    """
    if not Features().enable_partitions:
        return filepath

    str_path = str(filepath)

    # Anything that starts with a glob should be assumed to remain that same glob.
    if str_path.startswith("*"):
        return filepath

    if _has_partition(str_path):
        if "/" not in str_path:
            partition = str_path.strip("()")
            inner_path = ""
        else:
            partition, inner_path = str_path.split("/", maxsplit=1)
            partition = partition.strip("()")
    else:
        partition = "default"
        inner_path = str_path

    new_filepath = PurePosixPath(partition, inner_path)
    return filepath.__class__(new_filepath)
