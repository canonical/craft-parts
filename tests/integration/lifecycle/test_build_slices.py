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

import os.path
import subprocess
from pathlib import Path

import craft_parts
import distro
import pytest
import yaml
from craft_parts import Step

DATA_DIR = Path(__file__).parent / "data/build-slices"


def _get_uptime(proc_uptime: str) -> float:
    """Return the uptime in seconds from the /proc/uptime string."""
    return float(proc_uptime.split(maxsplit=1)[0])


@pytest.mark.skipif(
    distro.id() == "ubuntu" and distro.version() == "20.04",
    reason="focal has no golang-go chisel slices",
)
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

    start_uptime = _get_uptime(Path("/proc/uptime").read_text())

    with lifecycle.action_executor() as ctx:
        ctx.execute(lifecycle.plan(Step.PRIME))

    prime = tmp_homedir_path / "prime"

    assert (prime / "result").read_text() == "dependency\n"
    assert (prime / "plugin-file").read_text() == "dump plugin\n"
    # craftctl default in override-build runs plugin commands, then user commands
    assert (prime / "after-default").read_text() == "after-default\n"
    completed_process = subprocess.run(
        [prime / "bin/hello"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed_process.stdout == "hello from build slices\n"
    assert not (tmp_homedir_path / "stage/forbidden").exists()
    assert host_only_file.exists()

    assert (tmp_homedir_path / "build-slices").exists()
    assert not (tmp_homedir_path / "build-slices/stage").exists()

    # During the build step the stage dir is bind-mounted inside the build-slices
    # chroot: check that it's no longer mounted.
    chroot_work_dir = tmp_homedir_path / f"build-slices/{tmp_homedir_path}"
    assert not os.path.ismount(chroot_work_dir / "stage")

    # Check that the /proc filesystem was correctly mounted by verifying that the
    # 'uptime' inside the chroot is greater than the starting value
    chroot_uptime = (prime / "uptime").read_text()
    assert _get_uptime(chroot_uptime) > start_uptime

    # Same for /sys via /sys/class/net/lo/flags, which should have 0x8 for a loopback interface
    lo_flags = (prime / "lo_flags").read_text().strip()
    # 0x8 is IFF_LOOPBACK
    loopback = 0x8
    assert int(lo_flags, 16) & loopback
