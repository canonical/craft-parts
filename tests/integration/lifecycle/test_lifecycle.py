# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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
import pytest_check  # type: ignore[import]
import yaml
from craft_parts import Action, ActionProperties, ActionType, Features, Step

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


def test_basic_lifecycle_actions(new_dir, partitions, mocker):
    parts = yaml.safe_load(basic_parts_yaml)

    Path("a.tar.gz").touch()

    # no need to untar the file
    mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

    # See https://gist.github.com/sergiusens/dcae19c301eb59e091f92ab29d7d03fc

    # first run
    # command pull
    lf = craft_parts.LifecycleManager(
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
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        # fmt: off
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
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
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, reason="required to build 'bar'"),
        Action("foo", Step.STAGE, reason="required to build 'bar'"),
        Action("bar", Step.BUILD),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Building bar again rebuilds it (explicit request)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Modifying foo's source marks bar as dirty
    new_yaml = basic_parts_yaml.replace("source: a.tar.gz", "source: .")
    parts = yaml.safe_load(new_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD, ["bar"])
    assert actions == [
        # fmt: off
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.RERUN,
            reason="'source' property changed",
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
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD)
    assert actions == [
        # fmt: off
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]

    # Touching a source file triggers an update
    Path("a.tar.gz").touch()
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
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
            Step.BUILD,
            action_type=ActionType.UPDATE,
            reason="'PULL' step changed",
            properties=ActionProperties(changed_files=["a.tar.gz"], changed_dirs=[]),
        ),
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
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
        Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        # fmt: on
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)


def test_lifecycle_rerun_actions(new_dir, partitions, mocker):
    parts = yaml.safe_load(basic_parts_yaml)

    Path("a.tar.gz").touch()

    # no need to untar the file
    mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

    # See https://gist.github.com/sergiusens/dcae19c301eb59e091f92ab29d7d03fc

    # first run
    # command pull
    lf = craft_parts.LifecycleManager(
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

    # rerun skips pull...
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PULL)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
    ]

    # ...except if explicit rerun is set
    actions = lf.plan(Step.PULL, rerun=True)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.RERUN, reason="rerun step"),
        Action("bar", Step.PULL, action_type=ActionType.RERUN, reason="rerun step"),
        Action("foobar", Step.PULL, action_type=ActionType.RERUN, reason="rerun step"),
    ]


@pytest.mark.usefixtures("new_dir")
class TestCleaning:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        parts_yaml = textwrap.dedent(
            """
            parts:
              foo:
                plugin: dump
                source: foo
                override-build: |
                  craftctl default
                  touch $CRAFT_PART_INSTALL/../export/export_file
              bar:
                plugin: dump
                source: bar
            """
        )
        Path("foo").mkdir()
        Path("foo/foo.txt").touch()
        Path("bar").mkdir()
        Path("bar/bar.txt").touch()

        parts = yaml.safe_load(parts_yaml)

        self._lifecycle = craft_parts.LifecycleManager(
            parts,
            application_name="test_clean",
            cache_dir=new_dir,
            partitions=partitions,
        )

        # pylint: enable=attribute-defined-outside-init

    @pytest.fixture
    def foo_files(self):
        return [
            Path("parts/foo/src/foo.txt"),
            Path("parts/foo/install/foo.txt"),
            Path("parts/foo/export/export_file"),
            Path("stage/foo.txt"),
            Path("prime/foo.txt"),
        ]

    @pytest.fixture
    def bar_files(self):
        return [
            Path("parts/bar/src/bar.txt"),
            Path("parts/bar/install/bar.txt"),
            Path("stage/bar.txt"),
            Path("prime/bar.txt"),
        ]

    @pytest.fixture
    def state_files(self):
        return ["build", "prime", "pull", "stage"]

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

    def test_clean_default(self, foo_files, state_files):
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        for file in foo_files:
            assert file.is_file()

        state_dir = Path("parts/foo/state")

        assert sorted(state_dir.rglob("*")) == [
            state_dir / file for file in state_files
        ]
        assert Path("parts").exists()
        assert Path("backstage").exists()
        assert Path("stage").exists()
        assert Path("prime").exists()

        self._lifecycle.clean()

        assert Path("parts").exists() is False
        assert Path("backstage").exists() is False
        assert Path("stage").exists() is False
        assert Path("prime").exists() is False

        assert list(state_dir.rglob("*")) == []

    def test_clean_part(self, foo_files, bar_files, state_files):
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        foo_state_dir = Path("parts/foo/state")
        bar_state_dir = Path("parts/bar/state")

        self._lifecycle.clean(part_names=["foo"])

        for non_file in foo_files:
            pytest_check.is_false(non_file.is_file())
        assert list(foo_state_dir.rglob("*")) == []

        for file in bar_files:
            pytest_check.is_true(file.is_file())
        assert sorted(bar_state_dir.rglob("*")) == [
            bar_state_dir / file for file in state_files
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
        step_is_stage_or_later = step >= Step.STAGE
        step_is_prime = step == Step.PRIME
        includes_overlay = Features().enable_overlay and step > Step.OVERLAY

        self._lifecycle.clean(step)

        assert Path("parts").exists() == step_is_overlay_or_later
        assert Path("parts/foo/src/foo.txt").exists() == step_is_overlay_or_later
        assert Path("parts/bar/src/bar.txt").exists() == step_is_overlay_or_later
        assert Path("parts/foo/install/foo.txt").exists() == step_is_stage_or_later
        assert Path("parts/bar/install/bar.txt").exists() == step_is_stage_or_later
        assert Path("backstage/export_file").exists() == step_is_prime
        assert Path("stage/foo.txt").exists() == step_is_prime
        assert Path("stage/bar.txt").exists() == step_is_prime
        assert Path("prime").is_file() is False

        all_states = []
        if step_is_overlay_or_later:
            all_states.append(foo_state_dir / "pull")
            all_states.append(bar_state_dir / "pull")
        if step_is_stage_or_later:
            all_states.append(foo_state_dir / "build")
            all_states.append(bar_state_dir / "build")
        if step_is_prime:
            all_states.append(foo_state_dir / "stage")
            all_states.append(bar_state_dir / "stage")
        if includes_overlay:
            all_states.append(foo_state_dir / "layer_hash")
            all_states.append(bar_state_dir / "layer_hash")
            all_states.append(foo_state_dir / "overlay")
            all_states.append(bar_state_dir / "overlay")

        assert sorted(Path("parts").rglob("*/state/*")) == sorted(all_states)


class TestUpdating:
    @pytest.fixture(autouse=True)
    def setup_lifecycle(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        parts_yaml = textwrap.dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        self._lifecycle = craft_parts.LifecycleManager(
            parts,
            application_name="test_update",
            cache_dir=new_dir,
            arch="arm64",
            partitions=partitions,
        )
        # pylint: enable=attribute-defined-outside-init

    def test_refresh_system_packages_list(self, new_dir, mocker):
        mock_refresh_packages_list = mocker.patch(
            "craft_parts.packages.Repository.refresh_packages_list"
        )

        self._lifecycle.refresh_packages_list()

        mock_refresh_packages_list.assert_called_once_with()
