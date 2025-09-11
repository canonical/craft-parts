# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

import os
import stat
import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Step

basic_parts_yaml = textwrap.dedent(
    """\
    parts:
      p1:
        plugin: dump
        source: source
        organize:
          '*': dest/"""
)


@pytest.mark.skipif(os.geteuid() != 0, reason="requires root permissions")
def test_organize_special_files(new_dir, mocker):
    parts = yaml.safe_load(basic_parts_yaml)

    source_dir = Path("source")
    source_dir.mkdir()
    (source_dir / "dev").mkdir()

    # File to be organized into overlay
    (source_dir / "foo.txt").touch()
    os.mknod(source_dir / "dev/null", 0o777 | stat.S_IFCHR, os.makedev(1, 3))
    os.mknod(source_dir / "dev/loop99", 0o777 | stat.S_IFBLK, os.makedev(7, 99))
    os.mkfifo(source_dir / "bar.fifo")
    (source_dir / "qux").symlink_to("quux")

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test",
        cache_dir=new_dir,
    )
    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert Path("prime/foo.txt").exists() is False
    assert Path("prime/dev").exists() is False
    assert Path("prime/bar.fifo").exists() is False
    assert Path("prime/qux").exists() is False

    assert Path("prime/dest/foo.txt").is_file()
    assert stat.S_ISCHR(os.stat("prime/dest/dev/null").st_mode)  # noqa: PTH116
    assert stat.S_ISBLK(os.stat("prime/dest/dev/loop99").st_mode)  # noqa: PTH116
    assert stat.S_ISFIFO(os.stat("prime/dest/bar.fifo").st_mode)  # noqa: PTH116
    assert Path("prime/dest/qux").readlink() == "quux"
