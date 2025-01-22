# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
from craft_parts import ProjectDirs, errors
from craft_parts.parts import Part
from craft_parts.utils.partition_utils import get_partition_dir_map

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
        pytest_check.equal(p.part_install_dir, new_dir / "parts/foo/install")
        pytest_check.equal(p.part_state_dir, new_dir / "parts/foo/state")
        pytest_check.equal(p.part_packages_dir, new_dir / "parts/foo/stage_packages")
        pytest_check.equal(p.part_snaps_dir, new_dir / "parts/foo/stage_snaps")
        pytest_check.equal(p.part_run_dir, new_dir / "parts/foo/run")
        pytest_check.equal(p.part_layer_dir, new_dir / "parts/foo/layer")
        pytest_check.equal(p.stage_dir, new_dir / "stage")
        pytest_check.equal(p.prime_dir, new_dir / "prime")
        pytest_check.equal(
            p.part_install_dirs,
            get_partition_dir_map(
                base_dir=new_dir, partitions=partitions, suffix="parts/foo/install"
            ),
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
        pytest_check.equal(p.part_install_dir, new_dir / work_dir / "parts/foo/install")
        pytest_check.equal(p.part_state_dir, new_dir / work_dir / "parts/foo/state")
        pytest_check.equal(
            p.part_packages_dir, new_dir / work_dir / "parts/foo/stage_packages"
        )
        pytest_check.equal(
            p.part_snaps_dir, new_dir / work_dir / "parts/foo/stage_snaps"
        )
        pytest_check.equal(p.part_run_dir, new_dir / work_dir / "parts/foo/run")
        pytest_check.equal(p.part_layer_dir, new_dir / work_dir / "parts/foo/layer")
        pytest_check.equal(p.stage_dir, new_dir / work_dir / "stage")
        pytest_check.equal(p.prime_dir, new_dir / work_dir / "prime")
        pytest_check.equal(
            p.part_install_dirs,
            get_partition_dir_map(
                base_dir=new_dir / work_dir,
                partitions=partitions,
                suffix="parts/foo/install",
            ),
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
        return ["default", "kernel", "a/b", "a/c-d", "f00d", "ha-ha"]

    @pytest.fixture
    def valid_fileset(self):
        """Return a fileset of valid partition names.

        Assumes partition_list has been passed to the LifecycleManager.

        This list contains variations of two scenarios:
        1. A filepath beginning with a valid partition name (i.e. `(default)/test`)
        2. A partition name occurring in a filepath but not at the beginning, which
           is not treated as a partitioned filepath (i.e `test/(default)`)
        """
        return [
            "test",
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
            "(f00d)/test",
            "(ha-ha)/test",
        ]

    @pytest.fixture
    def misused_fileset(self):
        """Return a fileset that misuses partition names.

        Partition names are misused when an entry begins with a partition name
        but is not wrapped in parentheses.

        Assumes partition_list has been passed to the LifecycleManager.

        """
        return [
            "default",
            "default/foo",
            "kernel",
            "kernel/foo",
            "f00d",
            "f00d/foo",
            "ha-ha",
            "ha-ha/foo",
        ]

    @pytest.fixture
    def misused_namespaced_fileset(self):
        """Return a fileset that misuses namespaced partitions.

        Partition names are misused when an entry begins with a partition name
        but is not wrapped in parentheses.

        Assumes partition_list has been passed to the LifecycleManager.
        """
        return [
            "a/b",
            "a/b/foo",
            "a/c-d",
            "a/c-d/foo",
        ]

    @pytest.fixture
    def invalid_fileset(self):
        """Return a fileset of invalid uses of partition names.

        These filepaths are not necessarily violating the naming convention for
        partitions, but the partitions here are unknown and thus invalid.

        Assumes partition_list has been passed to the LifecycleManager.
        """
        return [
            # unknown partition names
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
            # no inner paths
            "(default)",
            "(default)/",
            "(a/b)",
            "(a/b)/",
            "(a/b)//",
            "(a/c-d)",
            "(a/c-d)/",
            "(a/c-d)//",
            "(kernel)",
            "(kernel)/",
            "(kernel)//",
        ]

    def test_part_valid_partition_usage(self, valid_fileset, partition_list):
        """Proper use of partitions in parts should not raise an error."""
        part_data = {
            "organize": {
                f"test-{index}": item for index, item in enumerate(valid_fileset)
            },
            "stage": valid_fileset,
            "prime": valid_fileset,
        }

        Part("a", part_data, partitions=partition_list)

    def test_part_partition_misuse(self, misused_fileset, partition_list):
        """Warn if partitions are misused."""
        part_data = {
            "organize": {
                f"test-{index}": item for index, item in enumerate(misused_fileset)
            },
            "stage": misused_fileset,
            "prime": misused_fileset,
        }

        with pytest.warns(Warning) as warning:
            Part("a", part_data, partitions=partition_list)

        partition_warning = warning.list[0].message
        assert isinstance(partition_warning, errors.PartitionUsageWarning)
        assert partition_warning.brief == "Possible misuse of partitions"
        assert partition_warning.details == dedent(
            """\
            The following entries begin with a valid partition name but are not wrapped in parentheses. These entries will go into the default partition.
              parts.a.organize
                misused partition 'default' in 'default'
                misused partition 'default' in 'default/foo'
                misused partition 'kernel' in 'kernel'
                misused partition 'kernel' in 'kernel/foo'
              parts.a.stage
                misused partition 'default' in 'default'
                misused partition 'default' in 'default/foo'
                misused partition 'kernel' in 'kernel'
                misused partition 'kernel' in 'kernel/foo'
              parts.a.prime
                misused partition 'default' in 'default'
                misused partition 'default' in 'default/foo'
                misused partition 'kernel' in 'kernel'
                misused partition 'kernel' in 'kernel/foo'"""
        )

    @pytest.mark.xfail(
        reason="Namespaced partitions are not checked for misuse", strict=True
    )
    def test_part_namespaced_partition_misuse(self, misused_fileset, partition_list):
        """Warn if namespaced partitions are misused."""
        part_data = {
            "organize": {
                f"test-{index}": item for index, item in enumerate(misused_fileset)
            },
            "stage": misused_fileset,
            "prime": misused_fileset,
        }

        with pytest.warns(Warning) as warning:
            Part("a", part_data, partitions=partition_list)

        partition_warning = warning.list[0].message
        assert isinstance(partition_warning, errors.PartitionUsageWarning)
        assert partition_warning.brief == "Possible misuse of partitions"
        assert partition_warning.details == dedent(
            """\
            The following entries begin with a valid partition name but are not wrapped in parentheses. These entries will go into the default partition.
              parts.a.organize
                misused partition 'a/b' in 'a/b'
                misused partition 'a/b' in 'a/b/foo'
                misused partition 'a/c-d' in 'a/c-d'
                misused partition 'a/c-d' in 'a/c-d/foo'
              parts.a.stage
                misused partition 'a/b' in 'a/b'
                misused partition 'a/b' in 'a/b/foo'
                misused partition 'a/c-d' in 'a/c-d'
                misused partition 'a/c-d' in 'a/c-d/foo'
              parts.a.prime
                misused partition 'a/b' in 'a/b'
                misused partition 'a/b' in 'a/b/foo'
                misused partition 'a/c-d' in 'a/c-d'
                misused partition 'a/c-d' in 'a/c-d/foo'"""
        )

    def test_part_invalid_partition_usage_simple(self, partition_list):
        """Raise an error if partitions are improperly used in parts."""
        part_data = {
            "organize": {"test": "(foo)"},
            "stage": ["(bar)/test"],
            "prime": ["(baz)"],
        }

        with pytest.raises(errors.PartitionUsageError) as raised:
            Part("part-a", part_data, partitions=partition_list)

        assert raised.value.brief == "Invalid usage of partitions"
        assert raised.value.details == dedent(
            f"""\
              parts.part-a.organize
                unknown partition 'foo' in '(foo)'
              parts.part-a.stage
                unknown partition 'bar' in '(bar)/test'
              parts.part-a.prime
                unknown partition 'baz' in '(baz)'
                no path specified after partition in '(baz)'
            Valid partitions: {", ".join(partition_list)}"""
        )

    def test_part_invalid_partition_usage_complex(
        self, valid_fileset, invalid_fileset, partition_list
    ):
        """Raise an error if partitions are improperly used in parts."""
        part_data = {
            "organize": {
                f"test-{index}": item
                for index, item in enumerate(valid_fileset + invalid_fileset)
            },
            "stage": valid_fileset + invalid_fileset,
            "prime": valid_fileset + invalid_fileset,
        }

        with pytest.raises(errors.PartitionUsageError) as raised:
            Part("part-a", part_data, partitions=partition_list)

        unknown_partitions_organize = dedent(
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
        unknown_partitions_stage_and_prime = dedent(
            """\
            unknown partition '' in '()'
            unknown partition 'foo' in '(foo)'
            no path specified after partition in '(foo)'
            unknown partition 'bar' in '(bar)/test'
            unknown partition 'BAZ' in '(BAZ)'
            unknown partition 'foo' in '(foo)/'
            no path specified after partition in '(foo)/'
            unknown partition 'foo' in '(foo)/test'
            unknown partition 'foo-bar' in '(foo-bar)'
            no path specified after partition in '(foo-bar)'
            unknown partition 'foo-bar' in '(foo-bar)/'
            no path specified after partition in '(foo-bar)/'
            unknown partition 'foo-bar' in '(foo-bar)/test'
            unknown partition 'foo/bar' in '(foo/bar)'
            no path specified after partition in '(foo/bar)'
            unknown partition 'foo/bar' in '(foo/bar)/'
            no path specified after partition in '(foo/bar)/'
            unknown partition 'foo/bar' in '(foo/bar)/test'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)'
            no path specified after partition in '(foo/bar-baz)'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)/'
            no path specified after partition in '(foo/bar-baz)/'
            unknown partition 'foo/bar-baz' in '(foo/bar-baz)/test'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)'
            no path specified after partition in '(foo-bar/baz)'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)/'
            no path specified after partition in '(foo-bar/baz)/'
            unknown partition 'foo-bar/baz' in '(foo-bar/baz)/test'
            unknown partition '123' in '(123)/test'
            unknown partition '123' in '(123)/test/(456)'
            unknown partition '123' in '(123)/test/(default)'
            unknown partition '123' in '(123)/test/(kernel)'
            unknown partition '123' in '(123)/test/(a/b)'
            unknown partition '123' in '(123)/test/(a/c-d)'
            no path specified after partition in '(default)'
            no path specified after partition in '(default)/'
            no path specified after partition in '(a/b)'
            no path specified after partition in '(a/b)/'
            no path specified after partition in '(a/b)//'
            no path specified after partition in '(a/c-d)'
            no path specified after partition in '(a/c-d)/'
            no path specified after partition in '(a/c-d)//'
            no path specified after partition in '(kernel)'
            no path specified after partition in '(kernel)/'
            no path specified after partition in '(kernel)//'
            """
        )

        assert raised.value.brief == "Invalid usage of partitions"
        assert raised.value.details == (
            "  parts.part-a.organize\n"
            + indent(unknown_partitions_organize, "    ")
            + "  parts.part-a.stage\n"
            + indent(unknown_partitions_stage_and_prime, "    ")
            + "  parts.part-a.prime\n"
            + indent(unknown_partitions_stage_and_prime, "    ")
            + "Valid partitions: "
            + ", ".join(partition_list)
        )
