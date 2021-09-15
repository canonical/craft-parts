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

import pytest
import yaml

import craft_parts
from craft_parts import Action, Step
from craft_parts.sources import errors


def test_source_local_simple(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: dump
            source: dir1
        """
    )

    Path("dir1").mkdir()
    Path("dir1/foobar.txt").write_text("content")

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_local", cache_dir=new_dir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    foo_src_dir = Path("parts", "foo", "src")
    assert list(foo_src_dir.rglob("*")) == [foo_src_dir / "foobar.txt"]
    assert Path(foo_src_dir, "foobar.txt").read_text() == "content"


def test_source_local_missing(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: make
            source: not_here
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_local", cache_dir=new_dir
    )

    with pytest.raises(errors.InvalidSourceType) as raised, lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    assert raised.value.source == "not_here"


def test_source_local_update(new_dir):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: dump
            source: dir1
        """
    )

    Path("dir1").mkdir()
    Path("dir1/foobar.txt").write_text("content")

    parts = yaml.safe_load(_parts_yaml)

    # execute the lifecycle
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_local", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # add extra content to source dir
    Path("dir1/new_file").write_text("new content")
    Path("dir1/dir2").mkdir()
    Path("dir1/dir2/another_new_file").write_text("more content")

    # and add a build artifact to the part build dir
    Path("parts/foo/build/build_artifact").write_text("created during build")

    # execute the lifecycle
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_local", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # after updating the files should be in the part src and build dirs
    assert Path("parts/foo/src/new_file").is_file()
    assert Path("parts/foo/src/dir2/another_new_file").is_file()

    assert Path("parts/foo/build/new_file").is_file()
    assert Path("parts/foo/build/dir2/another_new_file").is_file()

    # the build artifact must remain in the part build dir
    assert Path("parts/foo/build/build_artifact").is_file()

    # now remove the extra content from source dir
    Path("dir1/new_file").unlink()
    Path("dir1/dir2/another_new_file").unlink()
    Path("dir1/dir2").rmdir()

    # execute the lifecycle
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_local", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # the files should have been removed from the part src and build dirs
    assert Path("parts/foo/src/new_file").is_file() is False
    assert Path("parts/foo/src/dir2/another_new_file").is_file() is False
    assert Path("parts/foo/src/dir2").is_dir() is False

    assert Path("parts/foo/build/new_file").is_file() is False
    assert Path("parts/foo/build/dir2/another_new_file").is_file() is False
    assert Path("parts/foo/build/dir2").is_dir() is False

    # we can't remove build artifacts
    assert Path("parts/foo/build/build_artifact").is_file()
