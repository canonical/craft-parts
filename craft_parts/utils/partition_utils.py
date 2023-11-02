# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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
"""Unit tests for partition utilities."""

import re
from typing import Optional, Sequence

from craft_parts import errors, features


def validate_partition_names(partitions: Optional[Sequence[str]]) -> None:
    """Validate the partition feature set.

    If the partition feature is enabled, then:
      - the first partition must be "default"
      - each partition must contain only lowercase alphabetical characters
      - partitions are unique

    :param partitions: Partition data to verify.

    :raises ValueError: If the partitions are not valid or the feature is not enabled.
    """
    if not features.Features().enable_partitions:
        if partitions:
            raise errors.FeatureError(
                "Partitions are defined but partition feature is not enabled."
            )
        return

    if not partitions:
        raise errors.FeatureError(
            "Partition feature is enabled but no partitions are defined."
        )

    if partitions[0] != "default":
        raise errors.FeatureError("First partition must be 'default'.")

    if len(partitions) != len(set(partitions)):
        raise errors.FeatureError("Partitions must be unique.")

    for partition in partitions:
        if not re.fullmatch("[a-z]+", partition):
            raise errors.FeatureError(
                f"Partition {partition!r} must only contain lowercase letters."
            )
