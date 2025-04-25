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

import sys
import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Action, ActionType, Step


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_feature):
    return


@pytest.fixture
def fake_call(mocker):
    return mocker.patch("subprocess.check_call")


@pytest.fixture(autouse=True)
def mock_overlay_support_prerequisites(mocker):
    mocker.patch.object(sys, "platform", "linux")
    mocker.patch("os.geteuid", return_value=0)
    mock_refresh = mocker.patch(
        "craft_parts.overlays.OverlayManager.refresh_packages_list"
    )
    yield
    # Make sure that refresh_packages_list() was *not* called, as it's an expensive call that
    # overlays without packages do not need.
    assert not mock_refresh.called


class TestOverlayLayerOrder:
    @pytest.fixture
    def lifecycle(self, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
              p2:
                plugin: nil
              p3:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)

        return craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

    def test_layer_order_bottom_layer(self, lifecycle):
        # prime p1
        actions = lifecycle.plan(Step.PRIME, ["p1"])
        assert actions == [
            Action("p1", Step.PULL),
            Action("p1", Step.OVERLAY),
            Action("p1", Step.BUILD),
            Action("p1", Step.STAGE),
            Action("p1", Step.PRIME),
        ]

    def test_layer_order_top_layer(self, lifecycle):
        # prime p3, requires p1 and p2 overlay
        actions = lifecycle.plan(Step.PRIME, ["p3"])
        assert actions == [
            Action("p3", Step.PULL),
            Action("p1", Step.PULL, reason="required to overlay 'p3'"),
            Action("p1", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p2", Step.PULL, reason="required to overlay 'p3'"),
            Action("p2", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p3", Step.OVERLAY),
            Action("p3", Step.BUILD),
            Action("p3", Step.STAGE),
            Action("p3", Step.PRIME),
        ]

    def test_layer_parameter_change(self, lifecycle, fake_call, new_dir):
        actions = lifecycle.plan(Step.OVERLAY, ["p3"])
        assert actions == [
            Action("p3", Step.PULL),
            Action("p1", Step.PULL, reason="required to overlay 'p3'"),
            Action("p1", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p2", Step.PULL, reason="required to overlay 'p3'"),
            Action("p2", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p3", Step.OVERLAY),
        ]
        with lifecycle.action_executor() as ctx:
            ctx.execute(actions)

        # plan again with no changes
        actions = lifecycle.plan(Step.OVERLAY, ["p3"])
        assert actions == [
            # fmt: off
            Action("p3", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "p3", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
            ),
            # fmt: on
        ]

        # change a parameter in the parts definition, p2 overlay will rerun
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
              p2:
                plugin: nil
                overlay-script: echo
              p3:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)

        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )
        actions = lf.plan(Step.OVERLAY, ["p3"])
        assert actions == [
            # fmt: off
            Action("p3", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "p3", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
            ),
            # fmt: on
        ]


class TestOverlayStageDependency:
    def test_part_overlay_stage_dependency_top(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
              p2:
                plugin: nil
              p3:
                plugin: nil
                overlay-script: echo overlay
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.STAGE, ["p3"])
        assert actions == [
            # fmt: off
            Action("p3", Step.PULL),
            Action("p1", Step.PULL, reason="required to overlay 'p3'"),
            Action("p1", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p2", Step.PULL, reason="required to overlay 'p3'"),
            Action("p2", Step.OVERLAY, reason="required to overlay 'p3'"),
            Action("p3", Step.OVERLAY),
            Action("p3", Step.BUILD),
            Action("p3", Step.STAGE),
            # fmt: on
        ]

    def test_part_overlay_stage_dependency_middle(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
              p2:
                plugin: nil
                overlay-script: echo overlay
              p3:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.STAGE, ["p2"])
        assert actions == [
            # fmt: off
            Action("p2", Step.PULL),
            Action("p1", Step.PULL, reason="required to overlay 'p2'"),
            Action("p1", Step.OVERLAY, reason="required to overlay 'p2'"),
            Action("p2", Step.OVERLAY),
            Action("p3", Step.PULL, reason="required to build 'p2'"),
            Action("p3", Step.OVERLAY, reason="required to build 'p2'"),
            Action("p2", Step.BUILD),
            Action("p2", Step.STAGE),
            # fmt: on
        ]

    def test_part_overlay_stage_dependency_bottom(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
                overlay-script: echo overlay
              p2:
                plugin: nil
              p3:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.STAGE, ["p1"])
        assert actions == [
            # fmt: off
            Action("p1", Step.PULL),
            Action("p1", Step.OVERLAY),
            Action("p2", Step.PULL, reason="required to build 'p1'"),
            Action("p2", Step.OVERLAY, reason="required to build 'p1'"),
            Action("p3", Step.PULL, reason="required to build 'p1'"),
            Action("p3", Step.OVERLAY, reason="required to build 'p1'"),
            Action("p1", Step.BUILD),
            Action("p1", Step.STAGE),
            # fmt: on
        ]


class TestOverlayInvalidationFlow:
    def test_pull_dirty_single_part(self, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts, application_name="test_layers", cache_dir=new_dir
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            Action("p1", Step.PULL),
            Action("p1", Step.OVERLAY),
            Action("p1", Step.BUILD),
            Action("p1", Step.STAGE),
            Action("p1", Step.PRIME),
        ]

        with lf.action_executor() as ctx:
            ctx.execute(actions)

        # change a property of interest
        parts_yaml = textwrap.dedent(
            """
            parts:
              p1:
                plugin: nil
                source: .
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            # fmt: off
            Action(
                "p1",
                Step.PULL,
                action_type=ActionType.RERUN,
                reason="'source' property changed",
            ),
            Action("p1", Step.OVERLAY),
            Action("p1", Step.BUILD),
            Action("p1", Step.STAGE),
            Action("p1", Step.PRIME),
            # fmt: on
        ]

    # invalidation example 2
    def test_pull_dirty_multipart(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                after: [B]
              B:
                plugin: nil
                overlay-script: echo overlay
              C:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            # fmt: off
            Action("B", Step.PULL),
            Action("A", Step.PULL),
            Action("C", Step.PULL),
            Action("B", Step.OVERLAY),
            Action("A", Step.OVERLAY),
            Action("C", Step.OVERLAY),
            Action("B", Step.BUILD),
            Action("B", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "B", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
            ),
            Action("B", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "B",
                Step.STAGE,
                action_type=ActionType.RUN,
                reason="required to build 'A'",
            ),
            Action("A", Step.BUILD),
            Action("C", Step.BUILD),
            Action("B", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("A", Step.STAGE),
            Action("C", Step.STAGE),
            Action("B", Step.PRIME),
            Action("A", Step.PRIME),
            Action("C", Step.PRIME),
            # fmt: on
        ]

        with lf.action_executor() as ctx:
            ctx.execute(actions)

        # change overlay packages in B
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                after: [B]
              B:
                plugin: nil
                overlay-packages: [hello]
                overlay-script: echo overlay
              C:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            # fmt: off
            Action(
                "B",
                Step.PULL,
                action_type=ActionType.RERUN,
                reason="'overlay-packages' property changed",
            ),
            Action("A", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("C", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.OVERLAY),
            Action(
                "A",
                Step.OVERLAY,
                action_type=ActionType.REAPPLY,
                reason="previous layer changed",
            ),
            Action(
                "C",
                Step.OVERLAY,
                action_type=ActionType.REAPPLY,
                reason="previous layer changed",
            ),
            Action("B", Step.BUILD),
            Action("B", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "B", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
            ),
            Action("B", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "B",
                Step.STAGE,
                action_type=ActionType.RUN,
                reason="required to build 'A'",
            ),
            Action(
                "A",
                Step.BUILD,
                action_type=ActionType.RERUN,
                reason="stage for part 'B' changed",
            ),
            Action("C", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("A", Step.STAGE),
            Action("C", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.PRIME),
            Action("A", Step.PRIME),
            Action("C", Step.PRIME, action_type=ActionType.SKIP, reason="already ran"),
            # fmt: on
        ]

    def test_overlay_clean(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
              B:
                plugin: nil
                overlay-script: echo overlay
              C:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            Action("A", Step.PULL),
            Action("B", Step.PULL),
            Action("C", Step.PULL),
            Action("A", Step.OVERLAY),
            Action("B", Step.OVERLAY),
            Action("C", Step.OVERLAY),
            Action("A", Step.BUILD),
            Action("B", Step.BUILD),
            Action("C", Step.BUILD),
            Action("A", Step.STAGE),
            Action("B", Step.STAGE),
            Action("C", Step.STAGE),
            Action("A", Step.PRIME),
            Action("B", Step.PRIME),
            Action("C", Step.PRIME),
        ]

        with lf.action_executor() as ctx:
            ctx.execute(actions)

        # invalidate B overlay
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
              B:
                plugin: nil
                overlay-script: echo changed
              C:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            # fmt: off
            Action("A", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("C", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "A", Step.OVERLAY, action_type=ActionType.SKIP, reason="already ran"
            ),
            Action(
                "B",
                Step.OVERLAY,
                action_type=ActionType.RERUN,
                reason="'overlay-script' property changed",
            ),
            Action(
                "C",
                Step.OVERLAY,
                action_type=ActionType.REAPPLY,
                reason="previous layer changed",
            ),
            Action("A", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "B", Step.BUILD, action_type=ActionType.RERUN, reason="overlay changed"
            ),
            Action("C", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
            Action("A", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.STAGE),
            Action("C", Step.STAGE, action_type=ActionType.SKIP, reason="already ran"),
            Action("A", Step.PRIME, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.PRIME),
            Action("C", Step.PRIME, action_type=ActionType.SKIP, reason="already ran"),
            # fmt: on
        ]

    def test_overlay_invalidation_facundos_scenario(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                overlay-script: echo "overlay A"
              B:
                plugin: nil
                overlay-script: echo "overlay B"
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            Action("A", Step.PULL),
            Action("B", Step.PULL),
            Action("A", Step.OVERLAY),
            Action("B", Step.OVERLAY),
            Action("A", Step.BUILD),
            Action("B", Step.BUILD),
            Action("A", Step.STAGE),
            Action("B", Step.STAGE),
            Action("A", Step.PRIME),
            Action("B", Step.PRIME),
        ]

        with lf.action_executor() as ctx:
            ctx.execute(actions)

        # invalidate p2 overlay
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                overlay-script: echo "overlay A changed"
              B:
                plugin: nil
                overlay-script: echo "overlay B"
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = lf.plan(Step.PRIME)
        assert actions == [
            # fmt: off
            Action("A", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action("B", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
            Action(
                "A",
                Step.OVERLAY,
                action_type=ActionType.RERUN,
                reason="'overlay-script' property changed",
            ),
            Action(
                "B",
                Step.OVERLAY,
                action_type=ActionType.REAPPLY,
                reason="previous layer changed",
            ),
            Action(
                "A", Step.BUILD, action_type=ActionType.RERUN, reason="overlay changed"
            ),
            Action(
                "B", Step.BUILD, action_type=ActionType.RERUN, reason="overlay changed"
            ),
            Action("A", Step.STAGE, action_type=ActionType.RUN),
            Action("B", Step.STAGE),
            Action("A", Step.PRIME),
            Action("B", Step.PRIME),
            # fmt: on
        ]


class TestOverlaySpecScenarios:
    def test_overlay_spec_scenario_1(self, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                after: [B]
              B:
                plugin: nil
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts, application_name="test_layers", cache_dir=new_dir
        )

        actions = _filter_skip(lf.plan(Step.STAGE))
        assert actions == [
            Action("B", Step.PULL),
            Action("A", Step.PULL),
            Action("B", Step.OVERLAY),
            Action("A", Step.OVERLAY),
            Action("B", Step.BUILD),
            Action("B", Step.STAGE, reason="required to build 'A'"),
            Action("A", Step.BUILD),
            Action("A", Step.STAGE),
        ]

    def test_overlay_spec_scenario_2_stage_all(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                overlay-script: echo A
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE))
        assert actions == [
            Action("A", Step.PULL),
            Action("B", Step.PULL),
            Action("A", Step.OVERLAY),
            Action("B", Step.OVERLAY),
            Action("A", Step.BUILD),
            Action("B", Step.BUILD),
            Action("A", Step.STAGE),
            Action("B", Step.STAGE),
        ]

    def test_overlay_spec_scenario_2_stage_a(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                overlay-script: echo A
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE, part_names=["A"]))
        assert actions == [
            Action("A", Step.PULL),
            Action("A", Step.OVERLAY),
            Action("B", Step.PULL, reason="required to build 'A'"),
            Action("B", Step.OVERLAY, reason="required to build 'A'"),
            Action("A", Step.BUILD),
            Action("A", Step.STAGE),
        ]

    def test_overlay_spec_scenario_3_stage_a(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                after: [B]
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE, part_names=["A"]))
        assert actions == [
            Action("A", Step.PULL),
            Action("B", Step.PULL, reason="required to overlay 'A'"),
            Action("B", Step.OVERLAY, reason="required to overlay 'A'"),
            Action("A", Step.OVERLAY),
            Action("B", Step.BUILD, reason="required to build 'A'"),
            Action("B", Step.STAGE, reason="required to build 'A'"),
            Action("A", Step.BUILD),
            Action("A", Step.STAGE),
        ]

    def test_overlay_spec_scenario_3_stage_b(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
                after: [B]
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE, part_names=["B"]))
        assert actions == [
            Action("B", Step.PULL),
            Action("B", Step.OVERLAY),
            Action("A", Step.PULL, reason="required to build 'B'"),
            Action("A", Step.OVERLAY, reason="required to build 'B'"),
            Action("B", Step.BUILD),
            Action("B", Step.STAGE),
        ]

    def test_overlay_spec_scenario_4_stage_a(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE, part_names=["A"]))
        assert actions == [
            Action("A", Step.PULL),
            Action("A", Step.OVERLAY),
            Action("A", Step.BUILD),
            Action("A", Step.STAGE),
        ]

    def test_overlay_spec_scenario_4_stage_b(self, fake_call, new_dir):
        parts_yaml = textwrap.dedent(
            """
            parts:
              A:
                plugin: nil
              B:
                plugin: nil
                overlay-script: echo B
            """
        )
        parts = yaml.safe_load(parts_yaml)
        lf = craft_parts.LifecycleManager(
            parts,
            application_name="test_layers",
            cache_dir=new_dir,
            base_layer_dir=Path("/base"),
            base_layer_hash=b"hash",
        )

        actions = _filter_skip(lf.plan(Step.STAGE, part_names=["B"]))
        assert actions == [
            Action("B", Step.PULL),
            Action("A", Step.PULL, reason="required to overlay 'B'"),
            Action("A", Step.OVERLAY, reason="required to overlay 'B'"),
            Action("B", Step.OVERLAY),
            Action("B", Step.BUILD),
            Action("B", Step.STAGE),
        ]


def _filter_skip(actions: list[Action]) -> list[Action]:
    return [a for a in actions if a.action_type != ActionType.SKIP]
