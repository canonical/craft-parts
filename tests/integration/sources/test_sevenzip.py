# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import subprocess
import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Action, Step


def test_source_sevenzip(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: make
            source: foobar.7z
        """
    )

    Path("foobar.txt").write_text("content")
    subprocess.run(["7z", "a", "foobar.7z", "foobar.txt"], check=True)

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_7z", cache_dir=new_dir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    foo_src_dir = Path("parts", "foo", "src")
    assert list(foo_src_dir.rglob("*")) == [foo_src_dir / "foobar.txt"]
    assert Path(foo_src_dir, "foobar.txt").read_text() == "content"


def test_source_sevenzip_error(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: make
            source: foobar.7z
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    Path("foobar.7z").write_text("not a 7z file")
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_7z", cache_dir=new_dir
    )

    with pytest.raises(craft_parts.PartsError) as raised, lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    assert raised.value.brief == (
        f"Failed to pull source: command ['7z', 'x', '-o{new_dir}/parts/foo/src', "
        f"'{new_dir}/parts/foo/src/foobar.7z'] exited with code 2."
    )
