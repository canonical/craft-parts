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

      foobar:
        plugin: nil"""
)


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_feature):
    return


def test_basic_lifecycle_actions(new_dir, mocker):
    parts = yaml.safe_load(basic_parts_yaml)

    Path("a.tar.gz").touch()

    # no need to untar the file
    mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

    # See https://gist.github.com/sergiusens/dcae19c301eb59e091f92ab29d7d03fc

    # first run
    # command pull
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
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
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        # fmt: off
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.OVERLAY,
            action_type=ActionType.RUN,
            reason="required to overlay 'foobar'",
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
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Then running build for bar that depends on foo
    # command: build bar
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
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
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Modifying foo's source marks bar as dirty
    new_yaml = basic_parts_yaml.replace("source: a.tar.gz", "source: .")
    parts = yaml.safe_load(new_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
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
            reason="required to build 'bar'",
        ),
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
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # A request to build all parts skips everything
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
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
        # fmt: on
    ]

    # Touching a source file triggers an update
    Path("a.tar.gz").touch()
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
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
            "bar", step=Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
        ),
        Action(
            "foobar",
            step=Step.OVERLAY,
            action_type=ActionType.SKIP,
            reason="already ran",
        ),
        Action(
            "foo",
            Step.BUILD,
            action_type=ActionType.UPDATE,
            reason="'PULL' step changed",
            properties=ActionProperties(changed_files=["a.tar.gz"], changed_dirs=[]),
        ),
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
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)


@pytest.mark.usefixtures("new_dir")
class TestCleaning:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, mocker):
        mocker.patch("craft_parts.lifecycle_manager._ensure_overlay_supported")

        # pylint: disable=attribute-defined-outside-init
        parts_yaml = textwrap.dedent(
            """
            parts:
              foo:
                plugin: dump
                source: foo
                overlay-script: echo "test"
              bar:
                plugin: dump
                source: bar
                overlay-script: echo "test"
            """
        )
        Path("foo").mkdir()
        Path("foo/foo.txt").touch()
        Path("bar").mkdir()
        Path("bar/bar.txt").touch()

        parts = yaml.safe_load(parts_yaml)
        base_layer_dir = new_dir / "base_layer"
        base_layer_dir.mkdir()

        self._lifecycle = craft_parts.LifecycleManager(
            parts,
            application_name="test_clean",
            cache_dir=new_dir,
            base_layer_dir=base_layer_dir,
            base_layer_hash=b"hash",
        )

        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        ("step", "test_dir", "state_file"),
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install", "build"),
            (Step.STAGE, "stage", "stage"),
            (Step.PRIME, "prime", "prime"),
        ],
    )
    def test_clean_step(self, step, test_dir, state_file):
        actions = self._lifecycle.plan(step)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        assert Path(test_dir, "foo.txt").is_file()
        assert Path("parts/foo/state", state_file).is_file()

        self._lifecycle.clean(step, part_names=["foo"])

        assert Path(test_dir, "foo.txt").is_file() is False
        assert Path("parts/foo/state", state_file).is_file() is False

    def test_clean_default(self):
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        assert Path("parts/foo/src/foo.txt").is_file()
        assert Path("parts/foo/install/foo.txt").is_file()
        assert Path("stage/foo.txt").is_file()
        assert Path("prime/foo.txt").is_file()

        state_dir = Path("parts/foo/state")

        assert sorted(state_dir.rglob("*")) == [
            state_dir / "build",
            state_dir / "layer_hash",
            state_dir / "overlay",
            state_dir / "prime",
            state_dir / "pull",
            state_dir / "stage",
        ]

        self._lifecycle.clean()

        assert Path("parts").exists() is False
        assert Path("stage").exists() is False
        assert Path("prime").exists() is False

        assert list(state_dir.rglob("*")) == []

    def test_clean_part(self):
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        foo_state_dir = Path("parts/foo/state")
        bar_state_dir = Path("parts/bar/state")

        assert Path("overlay/stage_overlay").is_file()
        assert Path("overlay/prime_overlay").is_file()

        self._lifecycle.clean(part_names=["foo"])

        assert Path("parts/foo/src/foo.txt").is_file() is False
        assert Path("parts/foo/install/foo.txt").is_file() is False
        assert Path("stage/foo.txt").is_file() is False
        assert Path("prime/foo.txt").is_file() is False
        assert list(foo_state_dir.rglob("*")) == []

        assert Path("parts/bar/src/bar.txt").is_file()
        assert Path("parts/bar/install/bar.txt").is_file()
        assert Path("stage/bar.txt").is_file()
        assert Path("prime/bar.txt").is_file()
        assert sorted(bar_state_dir.rglob("*")) == [
            bar_state_dir / "build",
            bar_state_dir / "layer_hash",
            bar_state_dir / "overlay",
            bar_state_dir / "prime",
            bar_state_dir / "pull",
            bar_state_dir / "stage",
        ]

    @pytest.mark.parametrize("step", list(Step))
    def test_clean_all_parts(self, step):
        # always run all steps
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        foo_state_dir = Path("parts/foo/state")
        bar_state_dir = Path("parts/bar/state")

        step_is_overlay_or_later = step >= Step.OVERLAY
        step_is_build_or_later = step >= Step.BUILD
        step_is_stage_or_later = step >= Step.STAGE
        step_is_prime = step == Step.PRIME

        assert Path("overlay/stage_overlay").is_file()
        assert Path("overlay/prime_overlay").is_file()

        self._lifecycle.clean(step)

        assert Path("parts").exists() == step_is_overlay_or_later
        assert Path("parts/foo/src/foo.txt").exists() == step_is_overlay_or_later
        assert Path("parts/bar/src/bar.txt").exists() == step_is_overlay_or_later
        assert Path("parts/foo/install/foo.txt").exists() == step_is_stage_or_later
        assert Path("parts/bar/install/bar.txt").exists() == step_is_stage_or_later
        assert Path("stage/foo.txt").exists() == step_is_prime
        assert Path("stage/bar.txt").exists() == step_is_prime
        assert Path("overlay/stage_overlay").exists() == step_is_prime
        assert Path("overlay/prime_overlay").exists() is False
        assert Path("prime").exists() is False

        all_states = []
        if step_is_overlay_or_later:
            all_states.append(foo_state_dir / "pull")
            all_states.append(bar_state_dir / "pull")
        if step_is_build_or_later:
            all_states.append(foo_state_dir / "overlay")
            all_states.append(bar_state_dir / "overlay")
            all_states.append(foo_state_dir / "layer_hash")
            all_states.append(bar_state_dir / "layer_hash")
        if step_is_stage_or_later:
            all_states.append(foo_state_dir / "build")
            all_states.append(bar_state_dir / "build")
        if step_is_prime:
            all_states.append(foo_state_dir / "stage")
            all_states.append(bar_state_dir / "stage")

        assert sorted(Path("parts").rglob("*/state/*")) == sorted(all_states)


class TestUpdating:
    def test_refresh_system_packages_list(self, new_dir, mocker):
        mock_refresh_packages_list = mocker.patch(
            "craft_parts.packages.Repository.refresh_packages_list"
        )

        parts_yaml = textwrap.dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)

        lf = craft_parts.LifecycleManager(
            parts, application_name="test_update", cache_dir=new_dir, arch="arm64"
        )
        lf.refresh_packages_list()

        mock_refresh_packages_list.assert_called_once_with()
