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
from pathlib import PurePath
from typing import NamedTuple, TypeVar

from craft_parts.errors import FeatureError
from craft_parts.features import Features
from craft_parts.utils import partition_utils

FlexiblePath = TypeVar("FlexiblePath", PurePath, str)

# regex for a path beginning with a (area), like "(boot)/bin/sh"
HAS_AREA_REGEX = re.compile(
    r"^\(" + partition_utils.VALID_AREA_REGEX.pattern + r"\)(/.*)?$"
)


class AreaPathPair(NamedTuple):
    """A pair containing an area name and a path."""

    area: str | None
    path: PurePath | str


def _has_area(path: PurePath | str) -> bool:
    """Check whether a path has an explicit area."""
    return bool(HAS_AREA_REGEX.match(str(path)))


def get_area_and_path(path: FlexiblePath, default_partition: str) -> AreaPathPair:
    """Break an area path into the area and the child path.

    If the path begins with an area, that is used. Otherwise, the default
    partition is used.
    If partitions and overlay feature are not enabled, the area will be None.
    An area can either be a partition or the overlay.

    :param path: The filepath to parse.

    :returns: A tuple of (area, filepath)
    """
    if not Features().enable_partitions and not Features().enable_overlay:
        return AreaPathPair(None, path)

    str_path = str(path)

    if _has_area(str_path):
        area, inner_path = _split_area_and_inner_path(str_path)
        return AreaPathPair(area, path.__class__(inner_path))

    return AreaPathPair(default_partition, path)


def _split_area_and_inner_path(str_path: str) -> tuple[str, str]:
    """Split a path with an area into the area and inner path.

    :param str_path: A string of the filepath beginning with an area to split.

    :returns: A tuple containing the area and inner path. If there is no inner
    path, the second element will be an empty string.

    :raises FeatureError: If `str_path` does not begin with an area.
    """
    match = re.match(HAS_AREA_REGEX, str_path)

    if not match:
        raise FeatureError(f"Filepath {str_path!r} does not begin with an area.")

    area, inner_path = match.groups()

    # remove all forward slashes between the area and the inner path
    inner_path = (inner_path or "").lstrip("/")

    return area, inner_path
