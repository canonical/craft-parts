# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

from craft_parts.dirs import ProjectDirs


def test_dirs(new_dir):
    dirs = ProjectDirs()
    assert dirs.project_dir == new_dir
    assert dirs.work_dir == new_dir
    assert dirs.parts_dir == new_dir / "parts"
    assert dirs.overlay_dir == new_dir / "overlay"
    assert dirs.overlay_mount_dir == new_dir / "overlay/overlay"
    assert dirs.overlay_packages_dir == new_dir / "overlay/packages"
    assert dirs.overlay_work_dir == new_dir / "overlay/work"
    assert dirs.stage_dir == new_dir / "stage"
    assert dirs.prime_dir == new_dir / "prime"


def test_dirs_work_dir(new_dir):
    dirs = ProjectDirs(work_dir="foobar")
    assert dirs.project_dir == new_dir
    assert dirs.work_dir == new_dir / "foobar"
    assert dirs.parts_dir == new_dir / "foobar/parts"
    assert dirs.overlay_dir == new_dir / "foobar/overlay"
    assert dirs.overlay_mount_dir == new_dir / "foobar/overlay/overlay"
    assert dirs.overlay_packages_dir == new_dir / "foobar/overlay/packages"
    assert dirs.overlay_work_dir == new_dir / "foobar/overlay/work"
    assert dirs.stage_dir == new_dir / "foobar/stage"
    assert dirs.prime_dir == new_dir / "foobar/prime"


def test_dirs_work_dir_resolving():
    dirs = ProjectDirs(work_dir="~/x/../y/.")
    assert dirs.work_dir == Path.home() / "y"
