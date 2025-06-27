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
"""Unit tests for partition utilities."""

from pathlib import Path, PurePosixPath

import pytest
from craft_parts.errors import FeatureError
from craft_parts.utils.path_utils import (
    _has_partition,
    _split_partition_and_inner_path,
    get_partition_and_path,
)

PATH_CLASSES = [Path, PurePosixPath, str]

NON_PARTITION_PATHS = [
    "/absolute/path",
    "relative/path",
    "",
]

PARTITION_PATHS = [
    "(default)",
    "(default)/",
    "(default)//",
    "(default)/path",
    "(default)//path",
    "(partition)/path",
    "(parti-tion)/path",
    "(parti-tion)//path",
    "(parti-tion2)/path",
    "(test/partition)",
    "(test/partition)/",
    "(test/partition)//",
    "(test/partition)/path",
    "(test/partition)//path",
    "(test/parti-tion)/path",
    "(test/parti-tion)//path",
    "(test/parti-tion2)/path",
]

PARTITION_EXPECTED_PARTITIONS = [
    "default",
    "default",
    "default",
    "default",
    "default",
    "partition",
    "parti-tion",
    "parti-tion",
    "parti-tion2",
    "test/partition",
    "test/partition",
    "test/partition",
    "test/partition",
    "test/partition",
    "test/parti-tion",
    "test/parti-tion",
    "test/parti-tion2",
]

PARTITION_EXPECTED_INNER_PATHS = [
    "",
    "",
    "",
    "path",
    "path",
    "path",
    "path",
    "path",
    "path",
    "",
    "",
    "",
    "path",
    "path",
    "path",
    "path",
    "path",
]

# Prevent us from adding nonmatching paths for tests below.
assert len(PARTITION_PATHS) == len(PARTITION_EXPECTED_PARTITIONS), (
    "Expected partition paths and input partition paths need to match 1:1"
)
assert len(PARTITION_PATHS) == len(PARTITION_EXPECTED_INNER_PATHS), (
    "Expected partition paths and input partition paths need to match 1:1"
)


@pytest.mark.parametrize(
    ("full_path", "expected"),
    [
        ("some/path", False),
        ("not(a)partition", False),
        # regular partitions
        ("(default)", True),
        ("(default)/", True),
        ("(part)/some/path", True),
        ("(is1)/apartition", True),
        ("(woo-hoo)/im-a-partition", True),
        ("(nota)partition", False),
        ("(NOTA)/partition", False),
        ("(not!a)/partition", False),
        # namespaced partitions
        ("(is/a)/partition", True),
        ("(look/ma-n0-hands)", True),
        ("(foo/bar)/baz/qux", True),
        ("(is/a/valid)/partition", True),
        ("(is/not/a)partition", False),
        ("(not/a)partition", False),
        ("(NOT/a)partition", False),
        ("(not/A)partition", False),
        ("(not1/a)partition", False),
        ("(not/a1)partition", False),
        ("(-not/a)partition", False),
        ("(not-/a)partition", False),
        ("(-/nota)partition", False),
        ("(not/a-)partition", False),
        ("(not/-a)partition", False),
        ("(nota/-)partition", False),
    ],
)
def test_has_partition(full_path, expected):
    """Test that the partition regex has the expected results."""
    assert _has_partition(full_path) == expected


@pytest.mark.parametrize("path", NON_PARTITION_PATHS + PARTITION_PATHS)
@pytest.mark.parametrize("path_class", PATH_CLASSES)
def test_get_partition_compatible_filepath_disabled_passthrough(path, path_class):
    """Test that when partitions are disabled this is a no-op."""
    actual_partition, actual_inner_path = get_partition_and_path(
        path_class(path), "default"
    )

    assert actual_partition is None
    assert actual_inner_path == path_class(path)
    assert isinstance(actual_inner_path, path_class)


@pytest.mark.parametrize("path", ["*"])
@pytest.mark.parametrize("path_class", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_glob(path, path_class):
    expected = path_class(path)
    actual_partition, actual_inner_path = get_partition_and_path(expected, "default")

    assert actual_partition == "default"
    assert actual_inner_path == expected


@pytest.mark.parametrize("path", NON_PARTITION_PATHS)
@pytest.mark.parametrize("path_class", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_non_partition(path, path_class):
    """Non-partitioned paths get a default partition."""
    actual_partition, actual_inner_path = get_partition_and_path(
        path_class(path), "foo"
    )

    assert actual_partition == "foo"
    assert actual_inner_path == path_class(path)
    assert isinstance(actual_inner_path, path_class)


ZIPPED_PARTITIONS = zip(
    PARTITION_PATHS,
    PARTITION_EXPECTED_PARTITIONS,
    PARTITION_EXPECTED_INNER_PATHS,
)


@pytest.mark.parametrize("partition_paths", ZIPPED_PARTITIONS)
@pytest.mark.parametrize("path_class", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_partition(partition_paths, path_class):
    """Non-partitioned paths match their given partition."""
    path, expected_partition, expected_inner_path = partition_paths
    actual_partition, actual_inner_path = get_partition_and_path(
        path_class(path), "foo"
    )

    assert actual_partition == expected_partition
    assert actual_inner_path == path_class(expected_inner_path)
    assert isinstance(actual_inner_path, path_class)


def test_split_partition_and_inner_path_error():
    """Raise an error if the filepath does not begin with a partition."""
    with pytest.raises(FeatureError) as raised:
        _split_partition_and_inner_path("how?")

    assert raised.value.brief == "Filepath 'how?' does not begin with a partition."
