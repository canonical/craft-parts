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

"""Unit tests for the lifecycle manager with the partitions feature."""

from string import ascii_lowercase
from typing import Any, Dict

import pytest
from hypothesis import HealthCheck, given, settings, strategies

from craft_parts import errors
from craft_parts.lifecycle_manager import LifecycleManager


class TestPartitionsSupport:
    """Verify LifecycleManager supports partitions."""

    @pytest.fixture
    def parts_data(self) -> Dict[str, Any]:
        return {"parts": {"foo": {"plugin": "nil"}}}

    @pytest.mark.parametrize("partitions", [["default"], ["default", "kernel"]])
    def test_project_info(self, new_dir, parts_data, partitions):
        """Verify partitions are parsed and passed to ProjectInfo."""
        lifecycle = LifecycleManager(
            parts_data,
            application_name="test_manager",
            project_name="project",
            cache_dir=new_dir,
            work_dir="work_dir",
            arch="aarch64",
            parallel_build_count=16,
            custom="foo",
            partitions=partitions,
        )
        info = lifecycle.project_info

        assert info.application_name == "test_manager"
        assert info.project_name == "project"
        assert info.target_arch == "arm64"
        assert info.arch_triplet == "aarch64-linux-gnu"
        assert info.parallel_build_count == 16
        assert info.dirs.parts_dir == new_dir / "work_dir" / "parts"
        assert info.dirs.stage_dir == new_dir / "work_dir" / "stage"
        assert info.dirs.prime_dir == new_dir / "work_dir" / "prime"
        assert info.custom_args == ["custom"]
        assert info.custom == "foo"
        assert info.partitions == partitions

    @pytest.mark.parametrize("partitions", [None, []])
    def test_no_partitions(self, new_dir, parts_data, partitions):
        """Raise an error if the partitions feature is enabled but not defined."""
        with pytest.raises(errors.FeatureError) as raised:
            LifecycleManager(
                parts_data,
                application_name="test_manager",
                cache_dir=new_dir,
                partitions=partitions,
            )

        assert (
            raised.value.message
            == "Partition feature is enabled but no partitions are defined."
        )

    @pytest.mark.parametrize(
        "partitions", [["defaulta"], ["kernel"], ["kernel", "default"]]
    )
    def test_default_not_first(self, new_dir, parts_data, partitions):
        """Raise an error if the first partition is not 'default'."""
        with pytest.raises(ValueError) as raised:
            LifecycleManager(
                parts_data,
                application_name="test_manager",
                cache_dir=new_dir,
                partitions=partitions,
            )

        assert str(raised.value) == "First partition must be 'default'."

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        partitions=strategies.lists(
            strategies.text(strategies.sampled_from([*ascii_lowercase]), min_size=1),
            min_size=1,
        ).map(lambda lst: ["default"] + lst)
    )
    def test_partitions_valid(self, new_dir, parts_data, partitions):
        """Process valid partition names."""
        lifecycle = LifecycleManager(
            parts_data,
            application_name="test_manager",
            cache_dir=new_dir,
            partitions=partitions,
        )

        info = lifecycle.project_info

        assert info.partitions == partitions

    @pytest.mark.parametrize(
        "partitions",
        [
            ["Test"],
            ["TEST"],
            ["test1"],
            ["te-st"],
        ],
    )
    def test_partitions_invalid(self, new_dir, parts_data, partitions):
        """Raise an error if partitions are not lowercase alphabetical characters."""
        partitions.insert(0, "default")
        with pytest.raises(ValueError) as raised:
            LifecycleManager(
                parts_data,
                application_name="test_manager",
                cache_dir=new_dir,
                partitions=partitions,
            )

        assert (
            str(raised.value)
            == "Partitions must only contain lowercase alphabetical characters."
        )
