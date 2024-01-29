# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.utils import partition_utils


@pytest.mark.parametrize("partitions", [None, []])
def test_validate_partitions_success_feature_disabled(partitions):
    partition_utils.validate_partition_names(partitions)


@pytest.mark.parametrize(
    ("partitions", "message"),
    [
        (
            ["anything"],
            "Partitions are defined but partition feature is not enabled.",
        ),
    ],
)
def test_validate_partitions_failure_feature_disabled(partitions, message):
    with pytest.raises(errors.FeatureError) as exc_info:
        partition_utils.validate_partition_names(partitions)

    assert exc_info.value.message == message


@pytest.mark.usefixtures("enable_partitions_feature")
@pytest.mark.parametrize(
    "partitions",
    [
        ["default"],
        ["default", "mypart"],
        ["default", "mypart", "test/foo"],
        ["default", "mypart", "test/foo-bar"],
    ],
)
def test_validate_partitions_success_feature_enabled(partitions):
    partition_utils.validate_partition_names(partitions)


@pytest.mark.usefixtures("enable_partitions_feature")
@pytest.mark.parametrize(
    ("partitions", "message"),
    [
        ([], "Partition feature is enabled but no partitions are defined."),
        (["lol"], "First partition must be 'default'."),
        (["default", "default"], "Partitions must be unique."),
        (["default", "test/foo", "test/foo"], "Partitions must be unique."),
        (["default", "!!!"], "Partition '!!!' is invalid."),
        (["default", "test/!!!"], "Namespaced partition 'test/!!!' is invalid."),
        (
            ["default", "test", "test/foo"],
            "Partition 'test' conflicts with the namespace of partition 'test/foo'",
        ),
    ],
)
def test_validate_partitions_failure_feature_enabled(partitions, message):
    with pytest.raises(errors.FeatureError) as exc_info:
        partition_utils.validate_partition_names(partitions)

    assert exc_info.value.brief == message


@pytest.mark.parametrize("suffix", ["", "sub/sub/dir"])
def test_get_partitions_dir_map(new_dir, suffix):
    """Get a map of partitions directories."""
    dir_map = partition_utils.get_partition_dir_map(
        base_dir=new_dir, partitions=["default", "a", "b/c-d"], suffix=suffix
    )

    assert dir_map == {
        "default": Path(new_dir) / suffix,
        "a": Path(new_dir) / "partitions/a" / suffix,
        "b/c-d": Path(new_dir) / "partitions/b/c-d" / suffix,
    }


@pytest.mark.parametrize("suffix", ["", "sub/sub/dir"])
def test_get_partitions_dir_map_default_only(new_dir, suffix):
    """Get a partition map for only the default partition."""
    dir_map = partition_utils.get_partition_dir_map(
        base_dir=new_dir, partitions=["default"], suffix=suffix
    )

    assert dir_map == {"default": Path(new_dir) / suffix}


@pytest.mark.parametrize("suffix", ["", "sub/sub/dir"])
def test_get_partitions_dir_map_no_partitions(new_dir, suffix):
    """Get simple map when no partitions are provided."""
    dir_map = partition_utils.get_partition_dir_map(
        base_dir=new_dir, partitions=None, suffix=suffix
    )

    assert dir_map == {None: Path(new_dir) / suffix}
