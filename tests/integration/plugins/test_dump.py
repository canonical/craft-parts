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

import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Action, Step


@pytest.fixture
def install_dir():
    """Installation directory for the standard dump plugin."""
    return Path("parts", "foo", "install")


def test_dump_source(new_dir, partitions, install_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: dump
            source: subdir
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    source_dir = Path("subdir")
    source_dir.mkdir()
    Path(source_dir / "foobar.txt").touch()
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_dump", cache_dir=new_dir, partitions=partitions
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        ctx.execute(Action("foo", Step.BUILD))

    # only the file in subdir should be installed
    assert list(install_dir.rglob("*")) == [install_dir / "foobar.txt"]


def test_dump_ignore_dirs(new_dir, partitions, install_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: dump
            source: src
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    Path("src").mkdir()
    Path("src/foobar.txt").touch()
    Path("src/subdir").mkdir()
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_dump", cache_dir=new_dir, partitions=partitions
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        ctx.execute(Action("foo", Step.BUILD))

    # craft-parts subdirectories should be ignored
    assert Path("parts").is_dir()
    assert Path("stage").is_dir()
    assert Path("prime").is_dir()
    assert sorted(install_dir.rglob("*")) == [
        install_dir / "foobar.txt",
        install_dir / "subdir",
    ]
