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
"""Integration tests using chisel to stage packages."""

import logging
import os
import pathlib
import subprocess
import textwrap

import pytest
import yaml
from craft_parts.lifecycle_manager import LifecycleManager
from craft_parts.packages.errors import ChiselError
from craft_parts.steps import Step

pytestmark = [
    pytest.mark.usefixtures("add_overlay_feature"),
    pytest.mark.slow,
]

CHISEL_PART_YAML = """
parts:
  chiselled-part:
    plugin: nil
    stage-packages:
      - hello_bins
"""


@pytest.fixture(scope="module", autouse=True)
def _edge_chisel():
    # This fixture no longer needs to exist once chisel 1.3 or later is stable.
    subprocess.run(
        ["sudo", "snap", "refresh", "--edge", "chisel"],
        check=True,
    )
    yield
    subprocess.run(["sudo", "snap", "revert", "chisel"], check=True)


def test_slice_error_has_details(new_dir: pathlib.Path, partitions, caplog):
    caplog.set_level(logging.DEBUG)
    part_yaml = textwrap.dedent(
        """\
        parts:
          chiselled-part:
            plugin: nil
            stage-packages:
            - this-is-not-a-real-package_slice
        """
    )
    parts = yaml.safe_load(part_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_chisel",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
        parallel_build_count=os.cpu_count() or 1,
    )
    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        with pytest.raises(ChiselError) as exc_info:
            ctx.execute(actions)

    assert (
        exc_info.value.details
        == ':: error: slices of package "this-is-not-a-real-package" not found'
    )


def test_install_slice(new_homedir_path: pathlib.Path, partitions, caplog):
    caplog.set_level(logging.DEBUG)
    part_yaml = textwrap.dedent(
        """\
        parts:
          chiselled-part:
            plugin: nil
            stage-packages:
            - hello_bins
        """
    )
    parts = yaml.safe_load(part_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_chisel",
        cache_dir=new_homedir_path,
        work_dir=new_homedir_path,
        base_layer_dir=new_homedir_path / "base_layer",
        partitions=partitions,
        parallel_build_count=os.cpu_count() or 1,
    )

    actions = lf.plan(Step.STAGE)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    result = subprocess.run(
        [lf.project_info.stage_dir / "usr/bin/hello"],
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout == "Hello, world!\n"
