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

# Allow redefinition in order to include parent tests below.
# mypy: disable-error-code="no-redef"

import textwrap
from itertools import chain
from pathlib import Path

import craft_parts
import pytest
import pytest_check  # type: ignore[import]
import yaml
from craft_parts import Step

from tests.integration.lifecycle import test_lifecycle

# This wildcard import has pytest run any non-overridden lifecycle tests here.
# pylint: disable=wildcard-import,function-redefined,unused-import,unused-wildcard-import
from tests.integration.lifecycle.test_lifecycle import *  # noqa: F403  # pyright: ignore[reportGeneralTypeIssues,reportAssignmentType]

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


@pytest.mark.usefixtures("new_dir")
class TestCleaning:
    """Run all cleaning tests with partitions enabled."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        """Set up a source tree and a LifecycleManager.

        Includes parts with the same name across multiple partitions:
          - Part 'foo' creates the 'duplicate' file in 'default' and 'mypart'
          - Part 'bar' creates the 'duplicate' file in 'yourpart'
        This is to test that a cleaning a part only remove that part's files from shared
        directories (stage and prime) for each partition.
        """
        parts_yaml = textwrap.dedent(
            """
            parts:
              foo:
                plugin: dump
                source: foo
                organize:
                  (default)/file2: (mypart)/file2
                  (default)/duplicate1: (mypart)/duplicate
              bar:
                plugin: dump
                source: bar
                organize:
                  (default)/file4: (yourpart)/file4
                  (default)/duplicate: (yourpart)/duplicate
            """
        )
        Path("foo").mkdir()
        Path("foo/file1").touch()
        Path("foo/file2").touch()
        Path("foo/duplicate").touch()
        Path("foo/duplicate1").touch()
        Path("bar").mkdir()
        Path("bar/file3").touch()
        Path("bar/file4").touch()
        Path("bar/duplicate").touch()

        parts = yaml.safe_load(parts_yaml)

        # pylint: disable-next=attribute-defined-outside-init
        self._lifecycle = craft_parts.LifecycleManager(
            parts,
            application_name="test_clean",
            cache_dir=new_dir,
            partitions=partitions,
        )

    @pytest.fixture
    def foo_files(self):
        """Return a dictionary of steps and the files created by that step for foo."""
        return {
            Step.PULL: [
                Path("parts/foo/src/file1"),
                Path("parts/foo/src/file2"),
                Path("parts/foo/src/duplicate"),
                Path("parts/foo/src/duplicate1"),
            ],
            Step.BUILD: [
                Path("parts/foo/install/file1"),
                Path("parts/foo/install/duplicate"),
                Path("partitions/mypart/parts/foo/install/file2"),
                Path("partitions/mypart/parts/foo/install/duplicate"),
            ],
            Step.STAGE: [
                Path("stage/file1"),
                Path("stage/duplicate"),
                Path("partitions/mypart/stage/file2"),
                Path("partitions/mypart/stage/duplicate"),
            ],
            Step.PRIME: [
                Path("prime/file1"),
                Path("prime/duplicate"),
                Path("partitions/mypart/prime/file2"),
                Path("partitions/mypart/prime/duplicate"),
            ],
        }

    @pytest.fixture
    def bar_files(self):
        """Return a dictionary of steps and the files created by that step for bar."""
        return {
            Step.PULL: [
                Path("parts/bar/src/file3"),
                Path("parts/bar/src/file4"),
                Path("parts/bar/src/duplicate"),
            ],
            Step.BUILD: [
                Path("parts/bar/install/file3"),
                Path("partitions/yourpart/parts/bar/install/file4"),
                Path("partitions/yourpart/parts/bar/install/duplicate"),
            ],
            Step.STAGE: [
                Path("stage/file3"),
                Path("partitions/yourpart/stage/file4"),
                Path("partitions/yourpart/stage/duplicate"),
            ],
            Step.PRIME: [
                Path("prime/file3"),
                Path("partitions/yourpart/prime/file4"),
                Path("partitions/yourpart/prime/duplicate"),
            ],
        }

    @pytest.fixture
    def state_files(self):
        return ["build", "prime", "pull", "stage"]

    @pytest.mark.parametrize(
        "step",
        [
            Step.PULL,
            Step.BUILD,
            pytest.param(
                Step.STAGE,
                marks=pytest.mark.xfail(
                    reason=(
                        "Cleaning shared directories with the same file in multiple "
                        "partitions is not working."
                    ),
                    strict=True,
                ),
            ),
            pytest.param(
                Step.PRIME,
                marks=pytest.mark.xfail(
                    reason=(
                        "Cleaning shared directories with the same file in multiple "
                        "partitions is not working."
                    ),
                    strict=True,
                ),
            ),
        ],
    )
    def test_clean_step(self, step, foo_files):
        """Clean each step for a part."""
        actions = self._lifecycle.plan(step)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        assert all(file.is_file() for file in foo_files[step])
        assert Path(f"parts/foo/state/{step.name.lower()}").is_file()

        self._lifecycle.clean(step, part_names=["foo"])

        assert all(file.is_file() is False for file in foo_files[step])
        assert Path(f"parts/foo/state/{step.name.lower()}").is_file() is False

    def test_clean_default(self, foo_files, state_files):
        """Run the default clean behavior."""
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        for file in chain.from_iterable(foo_files.values()):
            assert file.is_file()

        state_dir = Path("parts/foo/state")

        assert sorted(state_dir.rglob("*")) == [
            state_dir / file for file in state_files
        ]

        self._lifecycle.clean()

        assert Path("parts").exists() is False
        assert Path("partitions").exists() is False
        assert Path("stage").exists() is False
        assert Path("prime").exists() is False

        assert list(state_dir.rglob("*")) == []

    @pytest.mark.xfail(
        reason="Cleaning shared directories with the same file in multiple partitions is not working.",
        strict=True,
    )
    def test_clean_part(self, foo_files, bar_files, state_files):
        """Clean a part."""
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        foo_state_dir = Path("parts/foo/state")
        bar_state_dir = Path("parts/bar/state")

        self._lifecycle.clean(part_names=["foo"])

        for non_file in chain.from_iterable(foo_files.values()):
            pytest_check.is_false(non_file.is_file())
        assert list(foo_state_dir.rglob("*")) == []

        for file in chain.from_iterable(bar_files.values()):
            pytest_check.is_true(file.is_file())
        assert sorted(bar_state_dir.rglob("*")) == [
            bar_state_dir / file for file in state_files
        ]

    @pytest.mark.parametrize(
        "step", [step for step in list(Step) if step != Step.OVERLAY]
    )
    def test_clean_all_parts(self, step, foo_files, bar_files):
        """Clean all steps for a part."""
        # always run all steps
        actions = self._lifecycle.plan(Step.PRIME)

        with self._lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        foo_state_dir = Path("parts/foo/state")
        bar_state_dir = Path("parts/bar/state")

        step_is_build_or_later = step >= Step.BUILD
        step_is_stage_or_later = step >= Step.STAGE
        step_is_prime = step == Step.PRIME

        self._lifecycle.clean(step)

        for file in chain(foo_files[Step.PULL], bar_files[Step.PULL]):
            assert file.exists() == step_is_build_or_later

        for file in chain(foo_files[Step.BUILD], bar_files[Step.BUILD]):
            assert file.exists() == step_is_stage_or_later

        for file in chain(foo_files[Step.STAGE], bar_files[Step.STAGE]):
            assert file.exists() == step_is_prime

        for file in chain(foo_files[Step.PRIME], bar_files[Step.PRIME]):
            # the prime step will always get cleaned
            assert file.exists() is False

        all_states = []
        if step_is_build_or_later:
            all_states.append(foo_state_dir / "pull")
            all_states.append(bar_state_dir / "pull")
        if step_is_stage_or_later:
            all_states.append(foo_state_dir / "build")
            all_states.append(bar_state_dir / "build")
        if step_is_prime:
            all_states.append(foo_state_dir / "stage")
            all_states.append(bar_state_dir / "stage")

        assert sorted(Path("parts").rglob("*/state/*")) == sorted(all_states)


class TestUpdating(test_lifecycle.TestUpdating):
    """Run all updating tests with partitions enabled."""


def test_track_stage_packages_with_partitions(new_dir):
    partitions = ["default", "binaries", "docs"]
    parts_yaml = textwrap.dedent(
        """
            parts:
              foo:
                plugin: nil
                stage-packages:
                  - hello
                organize:
                  usr/bin: (binaries)/
                  usr/share/doc: (docs)/
            """
    )
    parts = yaml.safe_load(parts_yaml)

    lifecycle = craft_parts.LifecycleManager(
        parts,
        application_name="test_track_stage_packages_with_partitions",
        cache_dir=new_dir,
        partitions=partitions,
        track_stage_packages=True,
    )

    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    packages = lifecycle.get_primed_stage_packages(part_name="foo")
    assert packages is not None

    name_only = [p.split("=")[0] for p in packages]
    assert "hello" in name_only
