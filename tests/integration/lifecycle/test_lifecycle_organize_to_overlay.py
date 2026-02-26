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

import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Action, ActionProperties, ActionType, Step

basic_parts_yaml = textwrap.dedent(
    """\
    parts:
      bar:
        after: [foo]
        plugin: nil

      foo:
        plugin: nil
        source: a.tar.gz
        organize:
          '*': (overlay)/

      foobar:
        plugin: nil"""
)


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_and_partitions_features):
    return


def test_basic_lifecycle_actions(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(basic_parts_yaml)
    Path("base").mkdir()
    Path("a.tar.gz").touch()

    # no need to untar the file
    mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

    lf_kwargs = {
        "application_name": "test_demo",
        "cache_dir": new_dir,
        "partitions": ["default"],
        "base_layer_dir": "base",
        "base_layer_hash": b"hash",
    }

    # first run
    # command pull
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.PULL)
    assert actions == [
        Action("foo", Step.PULL),
        Action("bar", Step.PULL),
        Action("foobar", Step.PULL),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # foobar part depends on nothing
    # command: prime foobar
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.OVERLAY,
            action_type=ActionType.RUN,
            reason="required to overlay 'foobar'",
        ),
        Action(
            "foo",
            Step.BUILD,
            action_type=ActionType.RUN,
            reason="organize contents to overlay",
        ),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "bar",
            Step.OVERLAY,
            action_type=ActionType.RUN,
            reason="required to overlay 'foobar'",
        ),
        Action("foobar", Step.OVERLAY),
        Action("foobar", Step.BUILD),
        Action("foobar", Step.STAGE),
        Action("foobar", Step.PRIME),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Then running build for bar that depends on foo
    # command: build bar
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, reason="required to build 'bar'"),
        Action("bar", Step.BUILD),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Building bar again rebuilds it (explicit request)
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Modifying foo's source marks bar as dirty
    new_yaml = basic_parts_yaml.replace("source: a.tar.gz", "source: .")
    parts = yaml.safe_load(new_yaml)

    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.RERUN,
            reason="'source' property changed",
        ),
        Action(
            "foo",
            Step.OVERLAY,
            action_type=ActionType.RUN,
            reason="required to build 'bar'",
        ),
        Action(
            "foo",
            Step.BUILD,
            action_type=ActionType.RUN,
            reason="organize contents to overlay",
        ),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.STAGE,
            action_type=ActionType.RUN,
            reason="required to build 'bar'",
        ),
        Action(
            "bar",
            Step.BUILD,
            action_type=ActionType.RERUN,
            reason="stage for part 'foo' changed",
        ),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # A request to build all parts skips everything
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foobar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
        ),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
    ]

    # Touching a source file triggers an update
    Path("a.tar.gz").touch()
    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.UPDATE,
            reason="source changed",
            properties=ActionProperties(changed_files=["a.tar.gz"], changed_dirs=[]),
        ),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            step=Step.OVERLAY,
            action_type=ActionType.UPDATE,
            reason="'PULL' step changed",
        ),
        Action(
            "foo",
            step=Step.BUILD,
            action_type=ActionType.UPDATE,
            reason="organize contents to overlay",
        ),
        Action(
            "bar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
        ),
        Action(
            "foobar",
            step=Step.OVERLAY,
            action_type=ActionType.SKIP,
            reason="already ran",
        ),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.STAGE,
            action_type=ActionType.RERUN,
            reason="'BUILD' step changed",
        ),
        Action(
            "bar",
            Step.BUILD,
            action_type=ActionType.RERUN,
            reason="stage for part 'foo' changed",
        ),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # A request to build all parts again skips everything
    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
        ),
        Action(
            "bar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
        ),
        Action(
            "foobar",
            step=Step.OVERLAY,
            action_type=ActionType.SKIP,
            reason="already ran",
        ),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)


def test_basic_lifecycle_overlay_only(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(basic_parts_yaml)
    Path("base").mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_demo",
        cache_dir=new_dir,
        partitions=["default"],
        base_layer_dir=Path("base"),
        base_layer_hash=b"hash",
    )

    actions = lf.plan(Step.PRIME, part_names=["bar"])
    assert actions == [
        Action("bar", Step.PULL),
        # dependencies to overlay bar
        Action("foo", Step.PULL, reason="required to overlay 'bar'"),
        Action("foo", Step.OVERLAY, reason="required to overlay 'bar'"),
        Action("foo", Step.BUILD, reason="organize contents to overlay"),
        Action("bar", Step.OVERLAY),
        # dependencies for "after"
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, reason="required to build 'bar'"),
        # now we can build bar
        Action("bar", Step.BUILD),
        Action("bar", Step.STAGE),
        # "after" causes the dependency to be primed too
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PRIME, reason="required to prime 'bar'"),  # wrong
        # the final requested action
        Action("bar", Step.PRIME),
    ]


unsorted_parts_yaml = textwrap.dedent(
    """\
    parts:
      p1:
        plugin: nil

      p2:
        plugin: nil
        organize:
          '*': (overlay)/

      p3:
        plugin: nil"""
)


def test_unsorted_lifecycle_actions(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(unsorted_parts_yaml)
    Path("base").mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_demo",
        cache_dir=new_dir,
        partitions=["default"],
        base_layer_dir=Path("base"),
        base_layer_hash=b"hash",
    )

    # first run
    # command pull
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("p2", Step.PULL),
        Action("p1", Step.PULL),
        Action("p3", Step.PULL),
        Action("p2", Step.OVERLAY),
        Action("p2", Step.BUILD, reason="organize contents to overlay"),
        Action("p1", Step.OVERLAY),
        Action("p3", Step.OVERLAY),
        Action("p2", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p1", Step.BUILD),
        Action("p3", Step.BUILD),
        Action("p2", Step.STAGE),
        Action("p1", Step.STAGE),
        Action("p3", Step.STAGE),
        Action("p2", Step.PRIME),
        Action("p1", Step.PRIME),
        Action("p3", Step.PRIME),
    ]


organize_twice_parts_yaml = textwrap.dedent(
    """\
    parts:
      p1:
        plugin: nil

      p2:
        plugin: nil
        organize:
          '*': (overlay)/

      p3:
        plugin: nil

      p4:
        plugin: nil
        organize:
          '*': (overlay)/"""
)


def test_organize_twice_lifecycle_actions(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(organize_twice_parts_yaml)
    Path("base").mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_demo",
        cache_dir=new_dir,
        partitions=["default"],
        base_layer_dir=Path("base"),
        base_layer_hash=b"hash",
    )

    # first run
    # command pull
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("p2", Step.PULL),
        Action("p4", Step.PULL),
        Action("p1", Step.PULL),
        Action("p3", Step.PULL),
        Action("p2", Step.OVERLAY),
        Action("p2", Step.BUILD, reason="organize contents to overlay"),
        Action("p4", Step.OVERLAY),
        Action("p4", Step.BUILD, reason="organize contents to overlay"),
        Action("p1", Step.OVERLAY),
        Action("p3", Step.OVERLAY),
        Action("p2", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p4", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p1", Step.BUILD),
        Action("p3", Step.BUILD),
        Action("p2", Step.STAGE),
        Action("p4", Step.STAGE),
        Action("p1", Step.STAGE),
        Action("p3", Step.STAGE),
        Action("p2", Step.PRIME),
        Action("p4", Step.PRIME),
        Action("p1", Step.PRIME),
        Action("p3", Step.PRIME),
    ]


organize_after_parts_yaml = textwrap.dedent(
    """\
    parts:
      p1:
        plugin: nil

      p2:
        plugin: nil
        after: [p3]
        organize:
          '*': (overlay)/

      p3:
        plugin: nil"""
)


def test_organize_after_lifecycle_actions(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(organize_after_parts_yaml)
    Path("base").mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_demo",
        cache_dir=new_dir,
        partitions=["default"],
        base_layer_dir=Path("base"),
        base_layer_hash=b"hash",
    )

    # first run
    # command pull
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("p3", Step.PULL),
        Action("p2", Step.PULL),
        Action("p1", Step.PULL),
        Action("p3", Step.OVERLAY),
        Action("p2", Step.OVERLAY),
        # p2 BUILD must come after p3 STAGE
        Action("p3", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("p3", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("p3", Step.BUILD, reason="required to build 'p2'"),
        Action("p3", Step.STAGE, reason="required to build 'p2'"),
        # end of p2 after dependency
        Action("p2", Step.BUILD, reason="organize contents to overlay"),
        Action("p1", Step.OVERLAY),
        Action("p3", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p2", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p1", Step.BUILD),
        Action("p3", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
        Action("p2", Step.STAGE),
        Action("p1", Step.STAGE),
        Action("p3", Step.PRIME),
        Action("p2", Step.PRIME),
        Action("p1", Step.PRIME),
    ]
