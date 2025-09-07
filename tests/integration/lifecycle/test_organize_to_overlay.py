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
from craft_parts import Action, ActionType, Step

basic_parts_yaml = textwrap.dedent(
    """\
    parts:
      p1:
        plugin: dump
        source: source
        organize:
          '*': (overlay)/"""
)


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_and_partitions_features):
    return


def test_organize_to_overlay(new_dir, mocker):
    mocker.patch("os.geteuid", return_value=0)

    parts = yaml.safe_load(basic_parts_yaml)

    base_layer_dir = Path("base")
    base_layer_dir.mkdir()

    source_dir = Path("source")
    source_dir.mkdir()

    # File to be organized into overlay
    (source_dir / "foo.txt").touch()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_demo",
        cache_dir=new_dir,
        partitions=["default"],
        base_layer_dir=base_layer_dir,
        base_layer_hash=b"hash",
    )
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("p1", Step.PULL),
        Action("p1", Step.OVERLAY),
        Action("p1", Step.BUILD, reason="organize contents to overlay"),
        Action("p1", Step.BUILD, action_type=ActionType.SKIP, reason="already ran"),
        Action("p1", Step.STAGE),
        Action("p1", Step.PRIME),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert Path("parts/p1/install/foo.txt").exists() is False
    assert Path("parts/p1/layer/foo.txt").exists()
    assert Path("prime/foo.txt").exists()
