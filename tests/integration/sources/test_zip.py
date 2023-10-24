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

import textwrap
import zipfile
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Action, Step


def test_source_zip(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: make
            source: foobar.zip
        """
    )

    Path("foobar.txt").write_text("content")
    with zipfile.ZipFile("foobar.zip", "w") as zipf:
        zipf.write("foobar.txt")

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_zip", cache_dir=new_dir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    foo_src_dir = Path("parts", "foo", "src")
    assert list(foo_src_dir.rglob("*")) == [foo_src_dir / "foobar.txt"]
    assert Path(foo_src_dir, "foobar.txt").read_text() == "content"


def test_source_zip_error(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: make
            source: foobar.zip
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    Path("foobar.zip").write_text("not a zip file")
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_zip", cache_dir=new_dir
    )

    with pytest.raises(zipfile.BadZipFile) as raised, lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    assert str(raised.value) == "File is not a zip file"
