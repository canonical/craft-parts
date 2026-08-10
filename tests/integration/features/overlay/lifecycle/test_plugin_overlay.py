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
"""Integration tests for plugin overlay commands without partitions (CRAFT-5027)."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Step, plugins
from craft_parts.overlays import errors as overlay_errors
from tests.integration.features.overlay_plugins import (
    ChrootCommandPlugin,
    PackageOverlayPlugin,
)

pytestmark = [
    pytest.mark.usefixtures("enable_overlay_feature"),
    pytest.mark.requires_root,
]


@pytest.fixture(scope="session")
def _chisel_cache(host_arch):
    """Session-scoped chisel base that downloads packages once."""
    arch = host_arch
    cache_dir = Path(tempfile.mkdtemp(prefix="craft-parts-chisel-", dir=Path.home()))
    subprocess.run(
        [
            "chisel",
            "cut",
            f"--root={cache_dir}",
            f"--arch={arch}",
            "base-files_base",
            "apt_apt-get",
            "bash_bins",
            "coreutils_bins",
        ],
        check=True,
    )
    (cache_dir / "dev").mkdir(exist_ok=True)
    (cache_dir / "proc").mkdir(exist_ok=True)
    (cache_dir / "sys").mkdir(exist_ok=True)
    yield cache_dir
    shutil.rmtree(cache_dir, ignore_errors=True)


@pytest.fixture
def chisel_base(new_homedir_path, _chisel_cache):
    """Per-test copy of the cached chisel base layer."""
    base_dir = new_homedir_path / "base"
    shutil.copytree(_chisel_cache, base_dir, symlinks=True)
    return base_dir


@pytest.fixture(autouse=True)
def register_plugins():
    """Register and unregister the test overlay plugins."""
    plugins.register(
        {
            "chroot-overlay": ChrootCommandPlugin,
            "package-overlay": PackageOverlayPlugin,
        }
    )
    yield
    plugins.unregister("chroot-overlay", "package-overlay")


DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    ("parts_file", "expected"),
    [
        pytest.param("parts-chroot-only.yaml", ["chroot-proof.txt"], id="chroot-only"),
        pytest.param(
            "parts-package-and-chroot.yaml",
            ["plugin-overlay-proof.txt"],
            id="package-and-chroot",
        ),
        pytest.param(
            "parts-override-overlay.yaml",
            ["chroot-proof.txt", "override-proof.txt"],
            id="override-overlay",
        ),
        pytest.param(
            "parts-package-override.yaml",
            ["plugin-overlay-proof.txt", "override-proof.txt"],
            id="package-override-overlay",
        ),
    ],
)
def test_plugin_overlay_commands(new_homedir_path, chisel_base, parts_file, expected):
    """Plugin overlay commands create expected files in the overlay layer."""
    parts = yaml.safe_load((DATA_DIR / parts_file).read_text())

    work_dir = new_homedir_path / "work"
    work_dir.mkdir()
    cache_dir = new_homedir_path / "cache"
    cache_dir.mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test",
        cache_dir=cache_dir,
        work_dir=work_dir,
        base_layer_dir=chisel_base,
        base_layer_hash=b"chisel-base",
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Check overlay layer
    work_parts = work_dir / "parts"
    for expected_file in expected:
        found = any(
            (work_parts / part_name / "layer" / expected_file).exists()
            for part_name in ("mypart",)
        )
        assert found, f"{expected_file} not found in any part's overlay layer"

    # Check files reached the prime directory
    prime_dir = work_dir / "prime"
    for expected_file in expected:
        assert (prime_dir / expected_file).exists(), (
            f"{expected_file} not found in prime directory"
        )


@pytest.mark.parametrize(
    ("scriptlet", "description"),
    [
        pytest.param(
            "craftctl set version=1.0",
            "craftctl set",
            id="craftctl-set",
        ),
        pytest.param(
            "craftctl get version",
            "craftctl get",
            id="craftctl-get",
        ),
        pytest.param(
            "craftctl stage",
            "craftctl stage",
            id="craftctl-stage",
        ),
    ],
)
def test_craftctl_invalid_in_override_overlay(
    new_homedir_path, chisel_base, scriptlet, description
):
    """Non-default craftctl commands fail in override-overlay."""
    parts_data = {
        "parts": {
            "mypart": {
                "plugin": "nil",
                "source": ".",
                "override-overlay": scriptlet,
            }
        }
    }

    work_dir = new_homedir_path / "work"
    work_dir.mkdir()
    cache_dir = new_homedir_path / "cache"
    cache_dir.mkdir()

    lf = craft_parts.LifecycleManager(
        parts_data,
        application_name="test",
        cache_dir=cache_dir,
        work_dir=work_dir,
        base_layer_dir=chisel_base,
        base_layer_hash=b"chisel-base",
    )

    actions = lf.plan(Step.OVERLAY)

    with pytest.raises(
        overlay_errors.OverlayChrootExecutionError,
        match="override-overlay",
    ):
        with lf.action_executor() as ctx:
            ctx.execute(actions)
