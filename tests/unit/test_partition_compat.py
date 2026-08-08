# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
"""Compatibility tests for the "partitions always enabled" refactor.

These tests pin the public API compatibility contract for callers that
were written against the pre-refactor code. Partitions are always active
internally; this file documents the surface-level shapes that must keep
working for external consumers:

- ``Features(enable_partitions=True)`` is an accepted no-op toggle.
- ``partitions=None`` is accepted as an alias for the default-only
  configuration in public constructors and helpers.
- ``partition=None`` is accepted by public getters as an alias for the
  default partition.
"""

import pytest
from craft_parts import Features, ProjectDirs, ProjectInfo
from craft_parts.parts import Part
from craft_parts.utils.partition_utils import (
    DEFAULT_PARTITION,
    get_partition_dir_map,
    is_default_partition,
    normalize_partition_names,
)


@pytest.fixture(autouse=True)
def _reset_features():
    Features.reset()
    yield
    Features.reset()


class TestFeaturesCompat:
    """The ``enable_partitions`` field is a no-op compatibility toggle."""

    def test_enable_partitions_true_is_accepted(self):
        """Setting ``enable_partitions=True`` does not raise."""
        features = Features(enable_partitions=True)
        assert features.enable_partitions is True

    def test_enable_partitions_false_is_accepted(self):
        """Setting ``enable_partitions=False`` does not raise."""
        features = Features(enable_partitions=False)
        assert features.enable_partitions is False

    def test_enable_partitions_does_not_affect_project_behavior(self, new_dir):
        """Toggling ``enable_partitions`` does not change ProjectInfo shape."""
        Features(enable_partitions=False)
        info_off = ProjectInfo(application_name="test", cache_dir=new_dir)
        assert info_off.partitions == ["default"]
        assert info_off.default_partition == "default"

        Features.reset()
        Features(enable_partitions=True)
        info_on = ProjectInfo(application_name="test", cache_dir=new_dir)
        assert info_on.partitions == ["default"]
        assert info_on.default_partition == "default"


class TestNormalizePartitionNamesCompat:
    """``normalize_partition_names`` is the single source of truth."""

    def test_none_yields_default(self):
        assert normalize_partition_names(None) == [DEFAULT_PARTITION]

    def test_empty_yields_default(self):
        assert normalize_partition_names([]) == [DEFAULT_PARTITION]

    def test_explicit_default_only(self):
        assert normalize_partition_names(["default"]) == ["default"]

    def test_explicit_multi_partition(self):
        assert normalize_partition_names(["default", "mypart"]) == [
            "default",
            "mypart",
        ]


class TestIsDefaultPartitionCompat:
    """``is_default_partition`` treats ``None`` as an alias for the default.

    Note: this is a behavior change from the pre-refactor implementation.
    Previously ``is_default_partition(["default"], None)`` returned False;
    the new contract is that ``partition=None`` always means "the default
    partition" regardless of the partition list.
    """

    def test_none_partitions_none_partition(self):
        assert is_default_partition(None, None) is True

    def test_default_only_none_partition(self):
        assert is_default_partition(["default"], None) is True

    def test_default_only_default(self):
        assert is_default_partition(["default"], "default") is True

    def test_multi_partition_default(self):
        assert is_default_partition(["default", "mypart"], "default") is True

    def test_multi_partition_non_default(self):
        assert is_default_partition(["default", "mypart"], "mypart") is False

    def test_aliased_default_none_partition(self):
        """When the first partition is not literally 'default', None still maps to it."""
        assert is_default_partition(["mypart", "yourpart"], None) is True

    def test_aliased_default_matches_first(self):
        assert is_default_partition(["mypart", "yourpart"], "mypart") is True


class TestProjectDirsCompat:
    """``ProjectDirs`` accepts ``partitions=None`` as default-only."""

    def test_partitions_none_yields_default(self, new_dir):
        dirs = ProjectDirs(partitions=None)
        assert dirs.partitions == ["default"]

    def test_partitions_none_stage_dir(self, new_dir):
        dirs = ProjectDirs(partitions=None)
        assert dirs.stage_dirs == {"default": dirs.stage_dir}

    def test_partitions_none_prime_dir(self, new_dir):
        dirs = ProjectDirs(partitions=None)
        assert dirs.prime_dirs == {"default": dirs.prime_dir}

    def test_get_stage_dir_partition_none(self, new_dir):
        dirs = ProjectDirs(partitions=None)
        assert dirs.get_stage_dir(partition=None) == dirs.stage_dir

    def test_get_prime_dir_partition_none(self, new_dir):
        dirs = ProjectDirs(partitions=None)
        assert dirs.get_prime_dir(partition=None) == dirs.prime_dir


class TestProjectInfoCompat:
    """``ProjectInfo`` accepts ``partitions=None`` as default-only."""

    def test_partitions_none_yields_default(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        assert info.partitions == ["default"]

    def test_default_partition(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        assert info.default_partition == "default"

    def test_partitions_return_type_is_list_of_str(self, new_dir):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        result = info.partitions
        assert isinstance(result, list)
        assert all(isinstance(p, str) for p in result)


class TestPartCompat:
    """``Part`` accepts ``partitions=None`` as default-only."""

    def test_part_default_partition_is_default(self):
        part = Part("p1", {"plugin": "nil"}, partitions=None)
        assert part.default_partition == "default"

    def test_part_install_dirs_default_only(self):
        part = Part("p1", {"plugin": "nil"}, partitions=None)
        assert list(part.part_install_dirs.keys()) == ["default"]

    def test_part_install_dirs_keys_are_str(self):
        part = Part("p1", {"plugin": "nil"}, partitions=None)
        assert all(isinstance(k, str) for k in part.part_install_dirs.keys())

    def test_part_stage_dirs_default_only(self):
        part = Part("p1", {"plugin": "nil"}, partitions=None)
        assert list(part.stage_dirs.keys()) == ["default"]

    def test_part_prime_dirs_default_only(self):
        part = Part("p1", {"plugin": "nil"}, partitions=None)
        assert list(part.prime_dirs.keys()) == ["default"]


class TestGetPartitionDirMapCompat:
    """``get_partition_dir_map`` accepts ``partitions=None`` as default-only."""

    def test_partitions_none_yields_default_key(self, new_dir):
        result = get_partition_dir_map(base_dir=new_dir, partitions=None)
        assert list(result.keys()) == ["default"]

    def test_partitions_none_maps_default_to_base(self, new_dir):
        result = get_partition_dir_map(
            base_dir=new_dir, partitions=None, suffix="stage"
        )
        assert result == {"default": new_dir / "stage"}

    def test_return_type_keys_are_str(self, new_dir):
        result = get_partition_dir_map(base_dir=new_dir, partitions=None)
        assert all(isinstance(k, str) for k in result.keys())
