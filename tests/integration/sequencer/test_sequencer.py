# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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
import time
from pathlib import Path

import pytest
from craft_parts import sequencer
from craft_parts.actions import Action, ActionType
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.steps import Step

_pull_state_foo = textwrap.dedent(
    """\
    part-properties:
      plugin: nil
      source-subdir: ''
      source-type: ''
      source-depth: 0
      source-branch: ''
      source-tag: ''
      source-commit: ''
      source-submodules: null
      stage-packages: []
      overlay-packages: []
    project_options:
      target_arch: amd64
    assets:
      stage-packages:
      - fake-package-foo=1
    """
)

_build_state_foo = textwrap.dedent(
    """\
    part-properties:
      plugin: nil
      after: []
      stage-packages: []
      disable-parallel: False
      build-packages: []
      organize: {}
      build-attributes: []
    project_options:
      target_arch: amd64
    assets: {}
    """
)

_pull_state_bar = textwrap.dedent(
    """\
    part-properties:
      plugin: nil
      source-subdir: ''
      source-type: ''
      source-depth: 0
      source-branch: ''
      source-tag: ''
      source-commit: ''
      source-submodules: null
      stage-packages: []
      overlay-packages: []
    project_options:
      target_arch: amd64
    assets:
      stage-packages:
      - fake-package-bar=2
    """
)


@pytest.fixture
def pull_state(new_dir):
    # build current state
    Path(new_dir / "parts/foo/state").mkdir(parents=True)
    Path(new_dir / "parts/bar/state").mkdir(parents=True)
    Path(new_dir / "parts/foo/state/pull").write_text(_pull_state_foo)
    Path(new_dir / "parts/bar/state/pull").write_text(_pull_state_bar)


@pytest.mark.usefixtures("new_dir")
class TestSequencerPlan:
    """Verify action planning sanity."""

    @pytest.fixture(autouse=True)
    def setup_project(self, partitions):
        self._project_info = (  # pylint: disable=attribute-defined-outside-init
            ProjectInfo(
                application_name="test", cache_dir=Path(), partitions=partitions
            )
        )

    def test_plan_default_parts(self, partitions):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)
        p2 = Part("bar", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.PRIME)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.RUN),
            Action("foo", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
            Action("foo", Step.PRIME, action_type=ActionType.RUN),
        ]

    def test_plan_dependencies(self, partitions):
        p1 = Part("foo", {"plugin": "nil", "after": ["bar"]}, partitions=partitions)
        p2 = Part("bar", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            project_info=self._project_info,
        )

        # pylint: disable=line-too-long
        # fmt: off
        actions = seq.plan(Step.PRIME)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.STAGE, action_type=ActionType.RUN, reason="required to build 'foo'"),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
            Action("foo", Step.PRIME, action_type=ActionType.RUN),
        ]
        # fmt: on

    def test_plan_specific_part(self, partitions):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)
        p2 = Part("bar", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.PRIME, part_names=["bar"])
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("bar", Step.STAGE, action_type=ActionType.RUN),
            Action("bar", Step.PRIME, action_type=ActionType.RUN),
        ]

    @pytest.mark.parametrize("rerun", [False, True])
    @pytest.mark.usefixtures("pull_state")
    def test_plan_requested_part_step(self, partitions, rerun):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.PULL, part_names=["foo"], rerun=rerun)

        if rerun:
            assert actions == [
                Action(
                    "foo", Step.PULL, action_type=ActionType.RERUN, reason="rerun step"
                ),
            ]
        else:
            assert actions == [
                Action(
                    "foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"
                ),
            ]

    @pytest.mark.usefixtures("pull_state")
    def test_plan_dirty_step(self, partitions):
        p1 = Part("foo", {"plugin": "dump"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.PULL)

        assert actions == [
            Action(
                part_name="foo",
                step=Step.PULL,
                action_type=ActionType.RERUN,
                reason="'plugin' property changed",
            ),
        ]

    @pytest.mark.usefixtures("pull_state")
    def test_plan_outdated_step(self, partitions):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)

        # touch pull step state
        Path("parts/foo/state/build").write_text(_build_state_foo)
        time.sleep(0.1)
        Path("parts/foo/state/pull").write_text(_pull_state_foo)

        seq = sequencer.Sequencer(
            part_list=[p1],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.BUILD)

        assert actions == [
            Action(
                part_name="foo",
                step=Step.PULL,
                action_type=ActionType.SKIP,
                reason="already ran",
            ),
            Action(
                part_name="foo",
                step=Step.BUILD,
                action_type=ActionType.UPDATE,
                reason="'PULL' step changed",
            ),
        ]


@pytest.mark.usefixtures("new_dir", "pull_state")
class TestSequencerStates:
    """Check existing state loading."""

    @pytest.fixture(autouse=True)
    def setup_project(self, partitions):
        self._project_info = (  # pylint: disable=attribute-defined-outside-init
            ProjectInfo(
                application_name="test", cache_dir=Path(), partitions=partitions
            )
        )

    def test_plan_load_state(self, partitions):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)
        p2 = Part("bar", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            project_info=self._project_info,
        )

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]

    def test_plan_reload_state(self, partitions):
        p1 = Part("foo", {"plugin": "nil"}, partitions=partitions)
        p2 = Part("bar", {"plugin": "nil"}, partitions=partitions)

        seq = sequencer.Sequencer(
            part_list=[p1, p2],
            project_info=self._project_info,
        )

        Path("parts/foo/state/pull").unlink()
        Path("parts/bar/state/pull").unlink()

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]

        seq.reload_state()

        actions = seq.plan(Step.BUILD)
        assert actions == [
            Action("bar", Step.PULL, action_type=ActionType.RUN),
            Action("foo", Step.PULL, action_type=ActionType.RUN),
            Action("bar", Step.BUILD, action_type=ActionType.RUN),
            Action("foo", Step.BUILD, action_type=ActionType.RUN),
        ]
