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
from typing import Optional, Sequence, Set, Tuple

from craft_parts import errors, features


def validate_partition_names(partitions: Optional[Sequence[str]]) -> None:
    """Validate the partition feature set.

    If the partition feature is enabled, then:
      - the first partition must be "default"
      - each partition must contain only lowercase alphabetical characters
      - partitions are unique

    Namespaced partitions can also be validated in addition to regular (or
    'non-namespaced') partitions. The format is `<namespace>/<partition>`.

    Namespaced partitions have the following naming convention:
      - the namespace must contain only lowercase alphabetical characters
      - the partition must contain only lowercase alphabetical characters and hyphens
      - the partition cannot begin or end with a hyphen

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

    namespaces: Set[Tuple[str, str]] = set()
    regular_partitions: Set[str] = set()

    for partition in partitions:
        # validate regular partitions
        if re.fullmatch("[a-z]+", partition):
            regular_partitions.add(partition)
        # validate namespaced partitions
        elif "/" in partition:
            match = re.fullmatch(r"([a-z]+)/(?!-)[a-z\-]+(?<!-)", partition)
            if match:
                # collect the namespace and the entire namespaced partition
                namespaces.add((match.group(1), match.string))
            else:
                raise errors.FeatureError(
                    message=f"Namespaced partition {partition!r} is invalid.",
                    details=(
                        "Namespaced partitions are formatted as `<namespace>/"
                        "<partition>`. Namespaces must only contain lowercase letters. "
                        "Namespaced partitions must only contain lowercase letters and "
                        "hyphens and cannot start or end with a hyphen."
                    ),
                )
        else:
            raise errors.FeatureError(
                message=f"Partition {partition!r} is invalid.",
                details="Partitions must only contain lowercase letters.",
            )

    # validate namespace conflicts (i.e. 'foo' in ['default', 'foo', 'foo/bar'])
    for regular_partition in regular_partitions:
        for namespace in namespaces:
            if regular_partition == namespace[0]:
                raise errors.FeatureError(
                    f"Partition {regular_partition!r} conflicts with the namespace of "
                    f"partition {namespace[1]!r}"
                )
