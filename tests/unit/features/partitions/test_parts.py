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

from textwrap import dedent

import pytest

from craft_parts import parts
from craft_parts.parts import Part
from tests.unit import test_parts


class TestPartSpecs(test_parts.TestPartSpecs):
    """Test part specification creation."""


class TestPartData(test_parts.TestPartData):
    """Test basic part creation and representation."""


class TestPartOrdering(test_parts.TestPartOrdering):
    """Test part ordering."""


class TestPartUnmarshal(test_parts.TestPartUnmarshal):
    """Verify data unmarshaling on part creation."""


class TestPartHelpers(test_parts.TestPartHelpers):
    """Test part-related helper functions."""


class TestPartValidation(test_parts.TestPartValidation):
    """Part validation considering plugin-specific attributes."""


class TestPartPartitionUsage:
    """Test usage of partitions in parts."""

    @pytest.fixture
    def partition_list(self):
        """Return a list of partitions, 'default' and 'kernel'."""
        return ["default", "kernel"]

    @pytest.fixture
    def valid_filesets(self):
        """Return a list of valid filesets when the partition feature is enabled.

        Assumes "default" and "partition" are valid partitions.
        """
        return [
            "test",
            "(default)",
            "(default)/test",
            "(default)/test/(otherdir)",
            "(default)/test/(otherdir-123)",
            "(default)/test/(default)",
            "(default)/test/(kernel)",
            "test(default)",
            "test(default)/test",
            "test/(default)/test",
            "(kernel)",
            "(kernel)/test",
            "(kernel)/test/(otherdir)",
            "(kernel)/test/(otherdir-123)",
            "(kernel)/test/(default)",
            "(kernel)/test/(kernel)",
            "test/(kernel)",
            "test(kernel)/test",
        ]

    @pytest.fixture
    def invalid_filesets(self):
        """Return a list of invalid filesets when the partition feature is enabled.

        Assumes "default" and "partition" are the only valid partitions.
        """
        return [
            "()",
            "(foo)",
            "(bar)/test",
            "(baz)",
            "(123)/test",
            "(123)/test/(456)",
            "(123)/test/(default)",
            "(123)/test/(kernel)",
        ]

    def test_part_valid_partition_usage(self, valid_filesets, partition_list):
        """Proper use of partitions in parts should not raise an error."""
        part_data = {
            "organize": {
                f"test-{index}": item for index, item in enumerate(valid_filesets)
            },
            "stage": valid_filesets,
            "prime": valid_filesets,
        }

        part_list = [Part("a", part_data), Part("b", part_data)]

        assert not parts.validate_partition_usage(part_list, partition_list)

    def test_part_invalid_partition_usage_simple(self, partition_list):
        """Raise an error if partitions are improperly used in parts."""
        part_data = {
            "organize": {"test": "(foo)"},
            "stage": ["(bar)/test"],
            "prime": ["(baz)"],
        }

        with pytest.raises(ValueError) as raised:
            parts.validate_partition_usage([Part("part-a", part_data)], partition_list)

        assert str(raised.value) == dedent(
            """\
            Error: Invalid usage of partitions:
              parts -> part-a -> organize
                unknown partition 'foo' in '(foo)'
              parts -> part-a -> stage
                unknown partition 'bar' in '(bar)/test'
              parts -> part-a -> prime
                unknown partition 'baz' in '(baz)'
            Valid partitions are 'default' and 'kernel'."""
        )

    def test_part_invalid_partition_usage_complex(
        self, valid_filesets, invalid_filesets, partition_list
    ):
        """Raise an error if partitions are improperly used in parts."""
        part_data = {
            "organize": {
                f"test-{index}": item
                for index, item in enumerate(valid_filesets + invalid_filesets)
            },
            "stage": valid_filesets + invalid_filesets,
            "prime": valid_filesets + invalid_filesets,
        }

        part_list = [Part("part-a", part_data), Part("part-b", part_data)]

        with pytest.raises(ValueError) as raised:
            parts.validate_partition_usage(part_list, partition_list)

        assert str(raised.value) == dedent(
            """\
            Error: Invalid usage of partitions:
              parts -> part-a -> organize
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts -> part-a -> stage
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts -> part-a -> prime
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts -> part-b -> organize
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts -> part-b -> stage
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts -> part-b -> prime
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
            Valid partitions are 'default' and 'kernel'."""
        )
