# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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
from craft_parts import Action, Step
from craft_parts.packages.errors import SnapDownloadError

from tests.fake_snap_command import FakeSnapCommand

_DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    ("stage_snaps_entry", "expected_download_args"),
    [
        pytest.param(
            "test-snap-with-component",
            ["snap", "download", "test-snap-with-component"],
            id="snap-only",
        ),
        pytest.param(
            "test-snap-with-component+comp1",
            ["snap", "download", "test-snap-with-component+comp1"],
            id="one-component",
        ),
        pytest.param(
            "test-snap-with-component+comp1+comp2",
            ["snap", "download", "test-snap-with-component+comp1+comp2"],
            id="two-components",
        ),
        pytest.param(
            "test-snap-with-component+comp1/beta",
            ["snap", "download", "test-snap-with-component+comp1", "--channel", "beta"],
            id="one-component-beta",
        ),
        pytest.param(
            "test-snap-with-component+comp1/edge",
            ["snap", "download", "test-snap-with-component+comp1", "--channel", "edge"],
            id="one-component-edge",
        ),
        pytest.param(
            "test-snap-with-component+comp1/candidate",
            [
                "snap",
                "download",
                "test-snap-with-component+comp1",
                "--channel",
                "candidate",
            ],
            id="one-component-candidate",
        ),
        pytest.param(
            "test-snap-with-component+comp1+comp2/beta",
            [
                "snap",
                "download",
                "test-snap-with-component+comp1+comp2",
                "--channel",
                "beta",
            ],
            id="two-components-beta",
        ),
    ],
)
def test_stage_snap_with_components(
    tmp_path: Path,
    partitions: list[str] | None,
    fake_snap_command: FakeSnapCommand,
    stage_snaps_entry: str,
    expected_download_args: list[str],
) -> None:
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: nil
            stage-snaps: [{stage_snaps_entry}]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_snap",
        cache_dir=tmp_path,
        work_dir=tmp_path,
        partitions=partitions,
    )

    actions = lf.plan(Step.PULL)
    assert actions == [Action("foo", Step.PULL)]

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])

    assert fake_snap_command.calls == [expected_download_args]


def test_stage_snap_mix_plain_and_component(
    tmp_path: Path,
    partitions: list[str] | None,
    fake_snap_command: FakeSnapCommand,
) -> None:
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-snaps:
              - basic
              - test-snap-with-component+comp1
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_snap",
        cache_dir=tmp_path,
        work_dir=tmp_path,
        partitions=partitions,
    )

    actions = lf.plan(Step.PULL)
    assert actions == [Action("foo", Step.PULL)]

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])

    assert fake_snap_command.calls == [
        ["snap", "download", "basic"],
        ["snap", "download", "test-snap-with-component+comp1"],
    ]


@pytest.mark.parametrize(
    (
        "stage_snaps_entry",
        "expected_snap_name",
        "expected_components",
        "expected_channel",
    ),
    [
        pytest.param(
            "test-snap-with-component+comp1",
            "test-snap-with-component",
            ["comp1"],
            "latest/stable",
            id="one-component-default-channel",
        ),
        pytest.param(
            "test-snap-with-component+comp1/beta",
            "test-snap-with-component",
            ["comp1"],
            "beta",
            id="one-component-beta",
        ),
        pytest.param(
            "test-snap-with-component+comp1+comp2",
            "test-snap-with-component",
            ["comp1", "comp2"],
            "latest/stable",
            id="two-components-default-channel",
        ),
    ],
)
def test_stage_snap_component_download_error(
    tmp_path: Path,
    partitions: list[str] | None,
    fake_snap_command: FakeSnapCommand,
    stage_snaps_entry: str,
    expected_snap_name: str,
    expected_components: list[str],
    expected_channel: str,
) -> None:
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: nil
            stage-snaps: [{stage_snaps_entry}]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_snap",
        cache_dir=tmp_path,
        work_dir=tmp_path,
        partitions=partitions,
    )

    actions = lf.plan(Step.PULL)
    assert actions == [Action("foo", Step.PULL)]

    fake_snap_command.download_side_effect = [False]

    with pytest.raises(SnapDownloadError) as raised, lf.action_executor() as ctx:
        ctx.execute(actions[0])

    assert raised.value.snap_name == expected_snap_name
    assert raised.value.snap_components == expected_components
    assert raised.value.snap_channel == expected_channel


def test_stage_snap_unpack_snap(
    tmp_path: Path,
    partitions: list[str] | None,
    fake_snap_command: FakeSnapCommand,
) -> None:
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-snaps: [hello]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_snap",
        cache_dir=tmp_path,
        work_dir=tmp_path,
        partitions=partitions,
    )

    actions = lf.plan(Step.BUILD)
    fake_snap_command.fake_download = str(_DATA_DIR / "hello.snap")

    install_dir = Path(tmp_path, "parts", "foo", "install")

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])  # PULL
        ctx.execute(actions[1])  # BUILD

    assert (install_dir / "meta.hello" / "snap.yaml").is_file()
    assert (install_dir / "bin" / "hello").is_file()


_SNAP_NAME = "test-snap-with-component"
_COMP_REVISION = "3"


@pytest.mark.parametrize(
    ("stage_snaps_entry", "component_names"),
    [
        pytest.param(
            "test-snap-with-component+comp1",
            ["comp1"],
            id="one-component",
        ),
        pytest.param(
            "test-snap-with-component+comp1+comp2",
            ["comp1", "comp2"],
            id="two-components",
        ),
    ],
)
def test_stage_snap_unpack_with_components(
    tmp_path: Path,
    partitions: list[str] | None,
    fake_snap_command: FakeSnapCommand,
    stage_snaps_entry: str,
    component_names: list[str],
) -> None:
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: nil
            stage-snaps: [{stage_snaps_entry}]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_snap",
        cache_dir=tmp_path,
        work_dir=tmp_path,
        partitions=partitions,
    )

    actions = lf.plan(Step.BUILD)
    fake_snap_command.fake_download = str(_DATA_DIR / f"{_SNAP_NAME}.snap")
    fake_snap_command.fake_comp_downloads = {
        f"{_SNAP_NAME}+{comp}": str(
            _DATA_DIR / f"{_SNAP_NAME}+{comp}_{_COMP_REVISION}.comp"
        )
        for comp in component_names
    }

    install_dir = Path(tmp_path, "parts", "foo", "install")

    with lf.action_executor() as ctx:
        ctx.execute(actions[0])  # PULL
        ctx.execute(actions[1])  # BUILD

    assert (install_dir / f"meta.{_SNAP_NAME}" / "snap.yaml").is_file()
    for comp in component_names:
        comp_meta_path = (
            Path("snap")
            / _SNAP_NAME
            / "components"
            / "mnt"
            / comp
            / _COMP_REVISION
            / "meta"
            / "component.yaml"
        )
        assert (install_dir / comp_meta_path).is_file()
