# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2024 Canonical Ltd.
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
import string
from pathlib import Path

import pytest
from craft_parts.dirs import ProjectDirs
from hypothesis import given, strategies


def test_dirs(new_dir, partitions):
    dirs = ProjectDirs(partitions=partitions)
    assert dirs.project_dir == new_dir
    assert dirs.work_dir == new_dir
    assert dirs.parts_dir == new_dir / "parts"
    assert dirs.overlay_dir == new_dir / "overlay"
    assert dirs.overlay_mount_dir == new_dir / "overlay/overlay"
    assert dirs.overlay_packages_dir == new_dir / "overlay/packages"
    assert dirs.overlay_work_dir == new_dir / "overlay/work"
    assert dirs.stage_dir == new_dir / "stage"
    assert set(dirs.stage_dirs.values()) == {dirs.stage_dir}
    assert dirs.prime_dir == new_dir / "prime"
    assert set(dirs.prime_dirs.values()) == {dirs.prime_dir}


def test_dirs_work_dir(new_dir, partitions):
    dirs = ProjectDirs(work_dir="foobar", partitions=partitions)
    assert dirs.project_dir == new_dir
    assert dirs.work_dir == new_dir / "foobar"
    assert dirs.parts_dir == new_dir / "foobar/parts"
    assert dirs.overlay_dir == new_dir / "foobar/overlay"
    assert dirs.overlay_mount_dir == new_dir / "foobar/overlay/overlay"
    assert dirs.overlay_packages_dir == new_dir / "foobar/overlay/packages"
    assert dirs.overlay_work_dir == new_dir / "foobar/overlay/work"
    assert dirs.stage_dir == new_dir / "foobar/stage"
    assert set(dirs.stage_dirs.values()) == {dirs.stage_dir}
    assert dirs.prime_dir == new_dir / "foobar/prime"
    assert set(dirs.prime_dirs.values()) == {dirs.prime_dir}


def test_dirs_work_dir_resolving(partitions):
    dirs = ProjectDirs(work_dir="~/x/../y/.", partitions=partitions)
    assert dirs.work_dir == Path.home() / "y"


@pytest.mark.usefixtures("enable_partitions_feature")
@given(
    partitions=strategies.lists(
        strategies.text(strategies.sampled_from(string.ascii_lowercase), min_size=1),
        min_size=1,
        unique=True,
    )
)
def test_get_stage_dir_with_partitions(partitions):
    dirs = ProjectDirs(partitions=["default", *partitions])

    for partition in partitions:
        assert dirs.get_stage_dir(partition=partition) == dirs.stage_dirs[partition]
    assert dirs.get_stage_dir(partition="default") == dirs.stage_dir
    assert dirs.get_stage_dir(partition="default") == dirs.stage_dirs["default"]


@pytest.mark.usefixtures("enable_partitions_feature")
@given(
    partitions=strategies.lists(
        strategies.text(strategies.sampled_from(string.ascii_lowercase), min_size=1),
        min_size=1,
        unique=True,
    )
)
def test_get_prime_dir_with_partitions(partitions):
    dirs = ProjectDirs(partitions=["default", *partitions])

    for partition in partitions:
        assert dirs.get_prime_dir(partition=partition) == dirs.prime_dirs[partition]
    assert dirs.get_prime_dir(partition="default") == dirs.prime_dir
    assert dirs.get_prime_dir(partition="default") == dirs.prime_dirs["default"]


def test_get_stage_dir_without_partitions():
    dirs = ProjectDirs(partitions=None)
    assert dirs.get_stage_dir() == dirs.stage_dir
    assert dirs.get_stage_dir(None) == dirs.stage_dir


def test_get_prime_dir_without_partitions():
    dirs = ProjectDirs(partitions=None)
    assert dirs.get_prime_dir() == dirs.prime_dir
    assert dirs.get_prime_dir(None) == dirs.prime_dir
