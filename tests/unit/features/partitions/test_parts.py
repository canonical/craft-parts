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

from textwrap import dedent, indent

import pytest
import pytest_check  # type: ignore[import]
from craft_parts import ProjectDirs, errors, parts
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

    @pytest.fixture()
    def partition_list(self):
        """Return a list of partitions, 'default' and 'kernel'."""
        return ["default", "kernel", "a/b", "a/c-d"]

    @pytest.fixture()
    def valid_filesets(self):
        """Return a list of valid filesets when the partition feature is enabled.

        Assumes "default", "a/b", "a/c-d", and "kernel" are passed to
        the LifecycleManager.

        This list contains variations of two scenarios:
        1. A filepath beginning with a valid partition name (i.e. `(default)/test`)
        2. A partition name occurring in a filepath but not at the beginning, which
           is not treated as a partitioned filepath (i.e `test/(default)`)
        """
        return [
            "test",
            "(default)",
            "(default)/",
            "(default)//",
            "(default)/test",
            "(default)//test",
            "(default)/test/(otherdir)",
            "(default)/test/(otherdir-123)",
            "(default)/test/(default)",
            "(default)/test/(kernel)",
            "(default)/test/(a/b)",
            "(default)/test/(a/c-d)",
            "test(default)",
            "test(default)/test",
            "test/(default)/test",
            "(kernel)",
            "(kernel)/",
            "(kernel)//",
            "(kernel)/test",
            "(kernel)//test",
            "(kernel)/test/(otherdir)",
            "(kernel)/test/(otherdir-123)",
            "(kernel)/test/(default)",
            "(kernel)/test/(kernel)",
            "(kernel)/test/(a/b)",
            "(kernel)/test/(a/c-d)",
            "test/(kernel)",
            "test(kernel)/test",
            "test/(kernel)/test",
            "(a/b)",
            "(a/b)/",
            "(a/b)//",
            "(a/b)/test",
            "(a/b)//test",
            "(a/b)/test/(otherdir)",
            "(a/b)/test/(otherdir-123)",
            "(a/b)/test/(default)",
            "(a/b)/test/(kernel)",
            "(a/b)/test/(a/b)",
            "(a/b)/test/(a/c-d)",
            "test/(a/b)",
            "test(a/b)/test",
            "test/(a/b)/test",
            "(a/c-d)",
            "(a/c-d)/",
            "(a/c-d)//",
            "(a/c-d)/test",
            "(a/c-d)//test",
            "(a/c-d)/test/(otherdir)",
            "(a/c-d)/test/(otherdir-123)",
            "(a/c-d)/test/(default)",
            "(a/c-d)/test/(kernel)",
            "(a/c-d)/test/(a/b)",
            "(a/c-d)/test/(a/c-d)",
            "test/(a/c-d)",
            "test(a/c-d)/test",
            "test/(a/c-d)/test",
            # filepaths beginning with partitions without parenthesis get organized
            # under the default partition
            "default",
            "kernel",
            "a",
            "a/b",
            "a/b",
            "a/c-d",
        ]

    @pytest.fixture()
    def invalid_filesets(self):
        """Return a list of invalid filesets when the partition feature is enabled.

        These filepaths are not necessarily violating the naming convention for
        partitions, but the partitions here are unknown (and thus invalid) to a
        LifecycleManager was created with the partitions "default", "a/b", "a/c-d",
        and "kernel".
        """
        return [
            "()",
            "(foo)",
            "(bar)/test",
            "(BAZ)",
            "(foo)/",
            "(foo)/test",
            "(foo-bar)",
            "(foo-bar)/",
            "(foo-bar)/test",
            "(foo/bar)",
            "(foo/bar)/",
            "(foo/bar)/test",
            "(foo/bar-baz)",
            "(foo/bar-baz)/",
            "(foo/bar-baz)/test",
            "(foo-bar/baz)",
            "(foo-bar/baz)/",
            "(foo-bar/baz)/test",
            "(123)/test",
            "(123)/test/(456)",
            "(123)/test/(default)",
            "(123)/test/(kernel)",
            "(123)/test/(a/b)",
            "(123)/test/(a/c-d)",
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

        with pytest.raises(errors.FeatureError) as raised:
            parts.validate_partition_usage(
                [Part("part-a", part_data, partitions=partition_list)], partition_list
            )

        assert raised.value.brief == dedent(
            """\
            Error: Invalid usage of partitions:
              parts.part-a.organize
                unknown partition 'foo' in '(foo)'
              parts.part-a.stage
                unknown partition 'bar' in '(bar)/test'
              parts.part-a.prime
                unknown partition 'baz' in '(baz)'
            Valid partitions are 'a/b', 'a/c-d', 'default', and 'kernel'."""
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

        with pytest.raises(errors.FeatureError) as raised:
            parts.validate_partition_usage(part_list, partition_list)

        unknown_partitions = dedent(
            """\
            unknown partition '' in '()'
            unknown partition 'foo' in '(foo)'
            unknown partition 'bar' in '(bar)/test'
            unknown partition 'BAZ' in '(BAZ)'
            unknown partition 'foo' in '(foo)/'
            unknown partition 'foo' in '(foo)/test'
            unknown partition 'foo-bar' in '(foo-bar)'
            unknown partition 'foo-bar' in '(foo-bar)/'
            unknown partition 'foo-bar' in '(foo-bar)/test'
            unknown partition 'foo/bar' in '(foo/bar)'
            unknown partition 'foo/bar' in '(foo/bar)/'
            unknown partition 'foo/bar' in '(foo/bar)/test'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)/'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)/test'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)/'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)/test'
            unknown partition '123' in '(123)/test'
            unknown partition '123' in '(123)/test/(456)'
            unknown partition '123' in '(123)/test/(default)'
            unknown partition '123' in '(123)/test/(kernel)'
            unknown partition '123' in '(123)/test/(a/b)'
            unknown partition '123' in '(123)/test/(a/c-d)'
            """
        )
        assert raised.value.message == (
            "Error: Invalid usage of partitions:\n"
            "  parts.part-a.organize\n"
            + indent(unknown_partitions, "    ")
            + "  parts.part-a.stage\n"
            + indent(unknown_partitions, "    ")
            + "  parts.part-a.prime\n"
            + indent(unknown_partitions, "    ")
            + "  parts.part-b.organize\n"
            + indent(unknown_partitions, "    ")
            + "  parts.part-b.stage\n"
            + indent(unknown_partitions, "    ")
            + "  parts.part-b.prime\n"
            + indent(unknown_partitions, "    ")
            + "Valid partitions are 'a/b', 'a/c-d', 'default', and 'kernel'."
        )
