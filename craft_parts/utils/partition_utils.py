# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Set

from craft_parts import errors, features

# regex for a valid partition name
_VALID_PARTITION_REGEX = re.compile(r"[a-z]+", re.ASCII)

# regex for a valid namespaced partition name
_VALID_NAMESPACED_PARTITION_REGEX = re.compile(r"[a-z]+/(?!-)[a-z\-]+(?<!-)", re.ASCII)


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

    _validate_partition_naming_convention(partitions)

    _validate_namespace_conflicts(partitions)


def _is_valid_partition_name(partition: str) -> bool:
    """Check if a partition name is valid.

    :param partition: partition to check

    :returns: true if the namespaced partition is valid
    """
    return bool(re.fullmatch(_VALID_PARTITION_REGEX, partition))


def _is_valid_namespaced_partition_name(partition: str) -> bool:
    """Check if a namespaced partition name is valid.

    :param partition: partition to check

    :returns: true if the namespaced partition is valid
    """
    return bool(re.fullmatch(_VALID_NAMESPACED_PARTITION_REGEX, partition))


def _validate_partition_naming_convention(partitions: Sequence[str]) -> None:
    """Validate naming convention of a sequence of partitions.

    :param partitions: Sequence of partitions to validate.

    :raises FeatureError: if a partition name is not valid
    """
    for partition in partitions:
        if _is_valid_partition_name(partition) or _is_valid_namespaced_partition_name(
            partition
        ):
            continue

        if "/" in partition:
            raise errors.FeatureError(
                message=f"Namespaced partition {partition!r} is invalid.",
                details=(
                    "Namespaced partitions are formatted as `<namespace>/"
                    "<partition>`. Namespaces must only contain lowercase letters. "
                    "Namespaced partitions must only contain lowercase letters and "
                    "hyphens and cannot start or end with a hyphen."
                ),
            )

        raise errors.FeatureError(
            message=f"Partition {partition!r} is invalid.",
            details="Partitions must only contain lowercase letters.",
        )


def _validate_namespace_conflicts(partitions: Sequence[str]) -> None:
    """Validate conflicts between regular partitions and namespaces.

    For example, `foo` conflicts in ['default', 'foo', 'foo/bar'].
    Assumes partition names are valid.

    :raises FeatureError: for namespace conflicts
    """
    namespaced_partitions: Set[str] = set()
    regular_partitions: Set[str] = set()

    # sort partitions
    for partition in partitions:
        if _is_valid_partition_name(partition):
            regular_partitions.add(partition)
        else:
            namespaced_partitions.add(partition)

    for regular_partition in regular_partitions:
        for namespaced_partition in namespaced_partitions:
            if namespaced_partition.startswith(regular_partition + "/"):
                raise errors.FeatureError(
                    f"Partition {regular_partition!r} conflicts with the namespace of "
                    f"partition {namespaced_partition!r}"
                )


def get_partition_dir_map(
    base_dir: Path, partitions: Optional[Iterable[str]], suffix: str = ""
) -> Dict[Optional[str], Path]:
    """Return a mapping of partition directories.

    The default partition maps to directories in the base_dir.
    All other partitions map to directories in `partitions/<partition-name>`.

    If no partitions are provided, return a mapping of `None` to `base_dir/suffix`.

    :param base_dir: Base directory.
    :param partitions: An iterable of partition names.
    :param suffix: String containing the subdirectory to map to inside
        each partition.

    :returns: A mapping of partition names to paths.
    """
    if partitions:
        return {
            "default": base_dir / suffix,
            **{
                partition: base_dir / "partitions" / partition / suffix
                for partition in partitions
                if partition != "default"
            },
        }

    return {None: base_dir / suffix}
