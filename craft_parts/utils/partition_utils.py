# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

import itertools
import re
from collections.abc import Sequence
from pathlib import Path

from craft_parts import errors, features

# Allow alphanumeric characters, hyphens and slashes, not starting or ending
# with a hyphen or a slash
VALID_PARTITION_REGEX = re.compile(r"(?!-|/)[a-z0-9-/]+(?<!-|/)", re.ASCII)
VALID_NAMESPACED_PARTITION_REGEX = re.compile(
    r"[a-z0-9]+/" + VALID_PARTITION_REGEX.pattern, re.ASCII
)

PARTITION_INVALID_MSG = (
    "Partitions must only contain lowercase letters, numbers,"
    "hyphens and slashes, and may not begin or end with a hyphen or a slash."
)

DEFAULT_PARTITION = "default"


def validate_partition_names(partitions: Sequence[str] | None) -> None:
    """Validate the partition feature set.

    If the partition feature is enabled, then:
      - each partition name must contain only lowercase alphanumeric characters
        hyphens and slashes, but not begin or end with a hyphen or a slash
      - partitions are unique
      - only the first partition can be named "default"

    Namespaced partitions can also be validated in addition to regular (or
    'non-namespaced') partitions. The format is `<namespace>/<partition>`.

    Namespaced partition names follow the same conventions described above.
    Namespace names must consist of only lowercase alphanumeric characters.

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

    if len(partitions) != len(set(partitions)):
        raise errors.FeatureError("Partitions must be unique.")

    for partition in partitions[1:]:
        if partition == DEFAULT_PARTITION:
            raise errors.FeatureError(
                "Only the first partition can be named 'default'."
            )

    _validate_partition_naming_convention(partitions)
    _validate_partitions_conflicts(partitions)


def _is_valid_partition_name(partition: str) -> bool:
    """Check if a partition name is valid.

    :param partition: partition to check

    :returns: true if the namespaced partition is valid
    """
    return bool(re.fullmatch(VALID_PARTITION_REGEX, partition))


def _is_valid_namespaced_partition_name(partition: str) -> bool:
    """Check if a namespaced partition name is valid.

    :param partition: partition to check

    :returns: true if the namespaced partition is valid
    """
    return bool(re.fullmatch(VALID_NAMESPACED_PARTITION_REGEX, partition))


def _validate_partition_naming_convention(partitions: Sequence[str]) -> None:
    """Validate naming convention of a sequence of partitions.

    :param partitions: Sequence of partitions to validate.

    :raises FeatureError: if a partition name is not valid
    """
    for partition in partitions:
        if _is_valid_namespaced_partition_name(partition):
            continue

        if "/" in partition:
            raise errors.FeatureError(
                message=f"Namespaced partition {partition!r} is invalid.",
                details=(
                    "Namespaced partitions are formatted as `<namespace>/"
                    "<partition>`. Namespaces must only contain lowercase letters "
                    "and numbers. " + PARTITION_INVALID_MSG
                ),
            )

        if _is_valid_partition_name(partition):
            continue
        raise errors.FeatureError(
            message=f"Partition {partition!r} is invalid.",
            details=PARTITION_INVALID_MSG,
        )


def _validate_partitions_conflicts(partitions: Sequence[str]) -> None:
    """Validate conflicts between partitions.

    Assumes partition names are valid and unique.

    :raises FeatureError: for conflicts
    """
    conflicting_partitions = _detect_conflicts(partitions)

    if not conflicting_partitions:
        return

    # Raise the full list of conflicts
    lines: list[str] = []
    for conflicts in conflicting_partitions:
        conflict_list = list(conflicts)
        conflict_list.sort()
        lines.append(f"- {str(conflict_list)[1:-1]}")

    msg = "\n".join(lines)

    raise errors.FeatureError(
        message=f"Partition name conflicts:\n{msg}",
        details="Hyphens and slashes are converted to underscores to associate partitions names with environment variables. 'foo-bar' and 'foo/bar' would result in environment variable FOO_BAR.",
    )


def _detect_conflicts(partitions: Sequence[str]) -> list[set[str]]:
    """Detect and return every conflicts between partitions.

    Rules:
      1: partition name must not conflict with namespace (or sub-namespace) names
        - `foo` and 'foo/bar' conflict
        - `foo/bar` and 'foo/bar/baz' conflict
      2: environment variables derived from partition names must not conflicts
        - `foo/bar-baz` and `foo/bar/baz` conflict (would be converted to FOO_BAR_BAZ)
        - `foo/bar/baz-qux` and `foo/bar-baz/qux` conflict (would be converted to FOO_BAR_BAZ_QUX)

    """
    conflict_sets: list[set[str]] = []
    env_var_translation = {ord("-"): "_", ord("/"): "_"}

    for candidate_partition, partition in itertools.combinations(partitions, 2):
        candidate_underscored = candidate_partition.translate(env_var_translation)
        underscored = partition.translate(env_var_translation)

        if (
            _namespace_conflicts(candidate_partition, partition)
            or candidate_underscored == underscored
        ):
            _register_conflict(conflict_sets, partition, candidate_partition)

    return conflict_sets


def _register_conflict(
    conflict_sets: list[set[str]], partition: str, candidate_partition: str
) -> None:
    """Register the conflict, avoiding duplicates.

    If the partition or the one it conflicts with is already in a known set of
    conflicts, expand this set.
    Otherwise, add a new set in the conflicts list.
    """
    new_conflict_set = {partition, candidate_partition}

    for conflict_set in conflict_sets:
        if partition in conflict_set or candidate_partition in conflict_set:
            conflict_set.update(new_conflict_set)
            break
    else:
        conflict_sets.append(new_conflict_set)


def _namespace_conflicts(a: str, b: str) -> bool:
    """Split candidates with slashes and check if the shorter one is a subset of the other."""
    separator = "/"
    a_list = a.split(separator)
    b_list = b.split(separator)

    if len(a_list) > len(b_list):
        return a_list[: len(b_list)] == b_list

    return b_list[: len(a_list)] == a_list


def get_partition_dir_map(
    base_dir: Path, partitions: Sequence[str] | None, suffix: str = ""
) -> dict[str | None, Path]:
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
            partitions[0]: base_dir / suffix,
            **{
                partition: base_dir / "partitions" / partition / suffix
                for partition in partitions[1:]
            },
        }

    return {None: base_dir / suffix}
