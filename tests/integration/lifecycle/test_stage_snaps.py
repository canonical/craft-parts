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
from craft_parts.packages.errors import SnapDownloadError
from craft_parts.sources.errors import PullError

_LOCAL_DIR = Path(__file__).parent


def test_stage_snap(new_dir, fake_snap_command):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-snaps: [basic]
        """
    )

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_snap", cache_dir=new_dir, work_dir=new_dir
    )

    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.OVERLAY),
        Action("foo", Step.BUILD),
    ]

    fake_snap_command.fake_download = str(_LOCAL_DIR / "data" / "basic.snap")

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])

    snaps = list(Path("parts/foo/stage_snaps").glob("*.snap"))
    assert len(snaps) == 1
    assert snaps[0].name == "basic.snap"

    ctx.execute(actions[2])

    foo_install_dir = Path(new_dir / "parts" / "foo" / "install")
    assert (foo_install_dir / "meta.basic" / "snap.yaml").is_file()


def test_stage_snap_download_error(new_dir, fake_snap_command):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-snaps: [basic]
        """
    )

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_snap", cache_dir=new_dir, work_dir=new_dir
    )

    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.OVERLAY),
        Action("foo", Step.BUILD),
    ]

    fake_snap_command.download_side_effect = [False]

    with pytest.raises(SnapDownloadError) as raised, lf.action_executor() as ctx:
        ctx.execute(actions[0])

    assert raised.value.snap_name == "basic"
    assert raised.value.snap_channel == "latest/stable"


def test_stage_snap_unpack_error(new_dir, fake_snap_command):
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-snaps: [bad-snap]
        """
    )

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_snap", cache_dir=new_dir, work_dir=new_dir
    )

    actions = lf.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.OVERLAY),
        Action("foo", Step.BUILD),
    ]

    Path("bad-snap.snap").write_text("not a snap")
    fake_snap_command.fake_download = str("bad-snap.snap")

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])

    snaps = list(Path("parts/foo/stage_snaps").glob("*.snap"))
    assert len(snaps) == 1
    assert snaps[0].name == "bad-snap.snap"

    with pytest.raises(PullError) as raised:
        ctx.execute(actions[2])
    assert raised.value.exit_code == 1
