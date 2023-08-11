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
import pytest_check  # type: ignore[import]

from craft_parts import ProjectDirs, parts
from craft_parts.parts import Part
from tests.unit import test_parts


# these no-op classes ensure that enabling the partitions feature does not change
# the functionality of Parts exercised by these tests
class TestPartSpecs(test_parts.TestPartSpecs):
    """Test part specification creation."""


class TestPartData(test_parts.TestPartData):
    """Test basic part creation and representation."""

    def test_part_dirs(self, new_dir, partitions):
        p = Part(
            "foo",
            {"plugin": "nil"},
            partitions=partitions,
            project_dirs=ProjectDirs(work_dir=new_dir, partitions=partitions),
        )
        pytest_check.equal(p.parts_dir, new_dir / "parts")
        pytest_check.equal(p.part_src_dir, new_dir / "parts/foo/src")
        pytest_check.equal(p.part_src_subdir, new_dir / "parts/foo/src")
        pytest_check.equal(p.part_build_dir, new_dir / "parts/foo/build")
        pytest_check.equal(p.part_build_subdir, new_dir / "parts/foo/build")
        pytest_check.equal(p.part_install_dir, new_dir / "parts/foo/install/default")
        pytest_check.equal(p.part_state_dir, new_dir / "parts/foo/state")
        pytest_check.equal(p.part_packages_dir, new_dir / "parts/foo/stage_packages")
        pytest_check.equal(p.part_snaps_dir, new_dir / "parts/foo/stage_snaps")
        pytest_check.equal(p.part_run_dir, new_dir / "parts/foo/run")
        pytest_check.equal(p.part_layer_dir, new_dir / "parts/foo/layer")
        pytest_check.equal(p.stage_dir, new_dir / "stage/default")
        pytest_check.equal(p.prime_dir, new_dir / "prime/default")
        pytest_check.equal(
            p.part_install_dirs,
            {
                partition: p.part_base_install_dir / partition
                for partition in partitions
            },
        )

    def test_part_work_dir(self, new_dir, partitions):
        work_dir = "foobar"
        p = Part(
            "foo",
            {},
            project_dirs=ProjectDirs(work_dir=work_dir, partitions=partitions),
            partitions=partitions,
        )
        pytest_check.equal(p.parts_dir, new_dir / work_dir / "parts")
        pytest_check.equal(p.part_src_dir, new_dir / work_dir / "parts/foo/src")
        pytest_check.equal(p.part_src_subdir, new_dir / work_dir / "parts/foo/src")
        pytest_check.equal(p.part_build_dir, new_dir / work_dir / "parts/foo/build")
        pytest_check.equal(p.part_build_subdir, new_dir / work_dir / "parts/foo/build")
        pytest_check.equal(
            p.part_install_dir, new_dir / work_dir / "parts/foo/install/default"
        )
        pytest_check.equal(p.part_state_dir, new_dir / work_dir / "parts/foo/state")
        pytest_check.equal(
            p.part_packages_dir, new_dir / work_dir / "parts/foo/stage_packages"
        )
        pytest_check.equal(
            p.part_snaps_dir, new_dir / work_dir / "parts/foo/stage_snaps"
        )
        pytest_check.equal(p.part_run_dir, new_dir / work_dir / "parts/foo/run")
        pytest_check.equal(p.part_layer_dir, new_dir / work_dir / "parts/foo/layer")
        pytest_check.equal(p.stage_dir, new_dir / work_dir / "stage/default")
        pytest_check.equal(p.prime_dir, new_dir / work_dir / "prime/default")
        pytest_check.equal(
            p.part_install_dirs,
            {
                partition: p.part_base_install_dir / partition
                for partition in partitions
            },
        )


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

        part_list = [
            Part("a", part_data, partitions=partition_list),
            Part("b", part_data, partitions=partition_list),
        ]

        assert parts.validate_partition_usage(part_list, partition_list) is None

    def test_part_invalid_partition_usage_simple(self, partition_list):
        """Raise an error if partitions are improperly used in parts."""
        part_data = {
            "organize": {"test": "(foo)"},
            "stage": ["(bar)/test"],
            "prime": ["(baz)"],
        }

        with pytest.raises(ValueError) as raised:
            parts.validate_partition_usage(
                [Part("part-a", part_data, partitions=partition_list)], partition_list
            )

        assert str(raised.value) == dedent(
            """\
            Error: Invalid usage of partitions:
              parts.part-a.organize
                unknown partition 'foo' in '(foo)'
              parts.part-a.stage
                unknown partition 'bar' in '(bar)/test'
              parts.part-a.prime
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

        part_list = [
            Part("part-a", part_data, partitions=partition_list),
            Part("part-b", part_data, partitions=partition_list),
        ]

        with pytest.raises(ValueError) as raised:
            parts.validate_partition_usage(part_list, partition_list)

        assert str(raised.value) == dedent(
            """\
            Error: Invalid usage of partitions:
              parts.part-a.organize
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts.part-a.stage
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts.part-a.prime
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts.part-b.organize
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts.part-b.stage
                unknown partition '' in '()'
                unknown partition 'foo' in '(foo)'
                unknown partition 'bar' in '(bar)/test'
                unknown partition 'baz' in '(baz)'
                unknown partition '123' in '(123)/test'
                unknown partition '123' in '(123)/test/(456)'
                unknown partition '123' in '(123)/test/(default)'
                unknown partition '123' in '(123)/test/(kernel)'
              parts.part-b.prime
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
