# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Integration tests for build-slices lifecycle behavior."""

import os
import subprocess
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Step

DATA_DIR = Path(__file__).parent / "data/build-slices"


@pytest.mark.requires_root
@pytest.mark.slow
@pytest.mark.usefixtures("enable_build_slices")
def test_build_step_runs_in_build_slices_chroot(tmp_homedir_path):
    """Build with slices in isolation and access the read-only stage directory."""
    host_only_file = DATA_DIR / "host-only"
    parts = yaml.safe_load((DATA_DIR / "parts.yaml").read_text())

    lifecycle = craft_parts.LifecycleManager(
        parts,
        application_name="test_build_slices",
        cache_dir=tmp_homedir_path,
        work_dir=tmp_homedir_path,
    )

    with lifecycle.action_executor() as ctx:
        ctx.execute(lifecycle.plan(Step.PRIME))

    assert (tmp_homedir_path / "prime/result").read_text() == "dependency\n"
    assert (tmp_homedir_path / "prime/plugin-file").read_text() == "dump plugin\n"
    completed_process = subprocess.run(
        [tmp_homedir_path / "prime/bin/hello"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed_process.stdout == "hello from build slices\n"
    assert not (tmp_homedir_path / "stage/forbidden").exists()
    assert host_only_file.exists()
    assert os.path.ismount(tmp_homedir_path / "stage") is False
