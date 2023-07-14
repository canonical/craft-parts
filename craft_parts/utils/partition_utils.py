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
from pathlib import Path
from typing import Union

from craft_parts.features import Features


# XXX: for context, you can see where this function in the prototype:
# https://github.com/mr-cal/craft-parts/commit/e2d15f1bb1da3207463ad3015b68509537b007c3


def get_partition_compatible_filepath(filepath: Union[Path, str]) -> Union[Path, str]:
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

    # XXX: I think this is the correct thing to do. The default globs should not be
    # modified (which comes from craft_parts/parts.py lines 55-58)
    if filepath == "*":
        return filepath

    # XXX: I know there is at least one problem with this regex: `(default)` and
    # `(default)/` are treated differently
    match = re.match("^\\((?P<partition>[a-z]+)\\)/(?P<filepath>.*)", str(filepath))
    if match:
        partition = match.group("partition")
        everything_else = match.group("filepath")
    else:
        partition = "default"
        everything_else = filepath

    new_filepath = Path(partition, everything_else)

    # XXX: craft-parts calls this function in different places. Sometimes the filepath
    # is a string and something it is a Path object. I decided to make this function
    # handle both scenarios but I wonder if this approach will create
    # type-checking issues in the future.
    return str(new_filepath) if isinstance(filepath, str) else new_filepath
