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
"""Unit tests for partition utilities."""
from pathlib import Path, PurePosixPath

import pytest
from utils.partition_utils import _has_partition, get_partition_compatible_filepath

PATH_CLASSES = [Path, PurePosixPath, str]

NON_PARTITION_PATHS = [
    "/absolute/path",
    "relative/path",
    "",
    "*",
]

PARTITION_PATHS = [
    "(default)",
    "(default)/",
    "(default)/path",
    "(partition)/path",
]

PARTITION_EXPECTED_PATHS = [
    "default",
    "default",
    "default/path",
    "partition/path",
]

# Prevent us from adding nonmatching paths for tests below.
assert len(PARTITION_PATHS) == len(
    PARTITION_EXPECTED_PATHS
), "Expected partition paths and input partition paths need to match 1:1"


@pytest.mark.parametrize(
    ("full_path", "expected"),
    [
        ("some/path", False),
        ("(default)", True),
        ("(default)/", True),
        ("(part)/some/path", True),
        ("(nota)partition", False),
        ("(not/a)partition", False),
        ("(not/a)/partition", False),
        ("(NOTA)/partition", False),
        ("(not1)/partition", False),
    ],
)
def test_has_partition(full_path, expected):
    """Test that the partition regex has the expected results."""
    assert _has_partition(full_path) == expected


@pytest.mark.parametrize("path", NON_PARTITION_PATHS + PARTITION_PATHS)
@pytest.mark.parametrize("cls", PATH_CLASSES)
def test_get_partition_compatible_filepath_disabled_passthrough(path, cls):
    """Test that when partitions are disabled this is a no-op."""
    actual = get_partition_compatible_filepath(cls(path))

    assert actual == cls(path)
    assert isinstance(actual, cls)


@pytest.mark.parametrize("path", ["*", "**", "*/path"])
@pytest.mark.parametrize("cls", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_glob_start(path, cls):
    expected = cls(path)
    actual = get_partition_compatible_filepath(expected)

    assert actual == expected


@pytest.mark.parametrize("path", NON_PARTITION_PATHS)
@pytest.mark.parametrize("cls", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_non_partition(path, cls):
    """Non-partitioned paths get a default partition."""
    actual = get_partition_compatible_filepath(cls(path))

    assert actual == cls(PurePosixPath("default", path))
    assert isinstance(actual, cls)


@pytest.mark.parametrize(
    ("path", "expected"),
    zip(PARTITION_PATHS, PARTITION_EXPECTED_PATHS),
)
@pytest.mark.parametrize("cls", PATH_CLASSES)
@pytest.mark.usefixtures("enable_partitions_feature")
def test_get_partition_compatible_filepath_partition(path, expected, cls):
    """Non-partitioned paths match their given partition."""
    actual = get_partition_compatible_filepath(cls(path))

    assert actual == cls(expected)
    assert isinstance(actual, cls)
