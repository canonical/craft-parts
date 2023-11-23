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

# Allow redefinition in order to include parent tests below.
# mypy: disable-error-code="no-redef"
from pathlib import Path

import pytest
import yaml
from craft_parts import Action, ActionProperties, ActionType, LifecycleManager, Step

from tests.integration.features.partitions.lifecycle import test_lifecycle

# pylint: disable=wildcard-import,function-redefined,unused-import,unused-wildcard-import
from tests.integration.features.partitions.lifecycle.test_lifecycle import *  # noqa: F403


def test_basic_lifecycle_actions(new_dir, partitions, mocker):
    parts = yaml.safe_load(test_lifecycle.basic_parts_yaml)

    Path("a.tar.gz").touch()

    # no need to untar the file
    mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

    # See https://gist.github.com/sergiusens/dcae19c301eb59e091f92ab29d7d03fc

    # first run
    # command pull
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
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
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        # fmt: off
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.RUN, reason="required to overlay 'foobar'"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.RUN, reason="required to overlay 'foobar'"),
        Action("foobar", Step.OVERLAY),
        Action("foobar", Step.BUILD),
        Action("foobar", Step.STAGE),
        Action("foobar", Step.PRIME),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Then running build for bar that depends on foo
    # command: build bar
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, reason="required to build 'bar'"),
        Action("foo", Step.STAGE, reason="required to build 'bar'"),
        Action("bar", Step.BUILD),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Building bar again rebuilds it (explicit request)
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.RERUN, reason="requested step"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Modifying foo's source marks bar as dirty
    new_yaml = test_lifecycle.basic_parts_yaml.replace("source: a.tar.gz", "source: .")
    parts = yaml.safe_load(new_yaml)

    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.RERUN, reason="'source' property changed"),
        Action("foo", Step.OVERLAY, action_type=ActionType.RUN, reason="required to build 'bar'"),
        Action("foo", Step.BUILD, action_type=ActionType.RUN, reason="required to build 'bar'"),
        Action("foo", Step.STAGE, action_type=ActionType.RUN, reason="required to build 'bar'"),
        Action("bar", Step.BUILD, action_type=ActionType.RERUN, reason="requested step"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # A request to build all parts skips everything
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]

    # Touching a source file triggers an update
    Path("a.tar.gz").touch()
    lf = LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
        Action("foo", Step.PULL, action_type=ActionType.UPDATE, reason="source changed",
               properties=ActionProperties(changed_files=["a.tar.gz"], changed_dirs=[])),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", step=Step.OVERLAY, action_type=ActionType.UPDATE, reason="'PULL' step changed"),
        Action("bar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.UPDATE, reason="'PULL' step changed",
               properties=ActionProperties(changed_files=["a.tar.gz"], changed_dirs=[])),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, action_type=ActionType.RERUN, reason="required to build 'bar'"),
        Action("bar", Step.BUILD, action_type=ActionType.RERUN, reason="stage for part 'foo' changed"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # A request to build all parts again skips everything
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)


@pytest.mark.usefixtures("new_dir")
class TestCleaning(test_lifecycle.TestCleaning):
    @pytest.fixture()
    def state_files(self):
        return ["build", "layer_hash", "overlay", "prime", "pull", "stage"]

    @pytest.fixture()
    def foo_files(self):
        return [
            Path("parts/foo/src/foo.txt"),
            Path("parts/foo/install/default/foo.txt"),
            Path("stage/default/foo.txt"),
            Path("prime/default/foo.txt"),
        ]

    @pytest.fixture()
    def bar_files(self):
        return [
            Path("parts/bar/src/bar.txt"),
            Path("parts/bar/install/default/bar.txt"),
            Path("stage/default/bar.txt"),
            Path("prime/default/bar.txt"),
        ]

    @pytest.mark.parametrize(
        "step,test_dir,state_file",
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install/default", "build"),
            (Step.STAGE, "stage/default", "stage"),
            (Step.PRIME, "prime/default", "prime"),
        ],
    )
    def test_clean_step(self, step, test_dir, state_file):
        super().test_clean_step(step, test_dir, state_file)
