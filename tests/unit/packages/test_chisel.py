# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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
import yaml
from craft_parts import Step
from craft_parts.packages import deb
from craft_parts.packages.deb import _is_list_of_slices


def test_is_list_of_slices():
    assert _is_list_of_slices(["package1_slice1", "package1_slice2", "package2_slice2"])
    assert not _is_list_of_slices(["package1", "package2"])
    assert not _is_list_of_slices([])


def test_fetch_stage_slices(tmp_path, fake_apt_cache):
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    slices = ["package1_slice1", "package2_slice2"]
    fetched_slices = deb.Ubuntu.fetch_stage_packages(
        cache_dir=Path(),
        package_names=slices,
        stage_packages_path=stage_dir,
        base="unused",
        arch="unused",
        list_only=False,
    )

    assert fetched_slices == slices
    # Sanity check: the chisel support doesn't include downloading the packages and slices yet.
    assert list(stage_dir.iterdir()) == []

    # Make sure the standard codepath for .deb packages was not followed.
    assert not fake_apt_cache.called


def test_unpack_stage_slices(tmp_path, fake_apt_cache, fake_deb_run, mocker):
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    install_dir = tmp_path / "install"
    install_dir.mkdir()

    slices = ["package1_slice1", "package2_slice2"]

    spied_normalize = mocker.spy(deb, "normalize")

    deb.Ubuntu.unpack_stage_packages(
        stage_packages_path=stage_dir, install_path=install_dir, stage_packages=slices
    )

    fake_deb_run.assert_called_once_with(
        [
            "chisel",
            "cut",
            "--root",
            str(install_dir),
            "package1_slice1",
            "package2_slice2",
        ]
    )

    # Make sure the contents of the cut slices have been normalized.
    spied_normalize.assert_called_once_with(install_dir, repository=deb.Ubuntu)


def test_chisel_pull_build(new_dir, fake_apt_cache, fake_deb_run):
    """Test the combination of 'pulling' and 'building' chisel slices."""
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-packages: [package1_slice1, package2_slice2]
        """
    )

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_slice", cache_dir=new_dir, work_dir=new_dir
    )

    actions = lf.plan(Step.BUILD)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    install_dir = lf.project_info.parts_dir / "foo/install"

    fake_deb_run.assert_called_once_with(
        [
            "chisel",
            "cut",
            "--root",
            str(install_dir),
            "package1_slice1",
            "package2_slice2",
        ]
    )
