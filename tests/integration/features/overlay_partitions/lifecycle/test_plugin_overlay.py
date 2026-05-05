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
"""Integration tests for plugin overlay commands with partitions (CRAFT-5027).

These tests use chisel slices organized to the overlay via partitions syntax,
then exercise plugin overlay packages, host commands, and chroot commands.
"""

from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts import Step, plugins

from tests.integration.features.overlay_plugins import (
    ChrootCommandPlugin,
    HostCommandPlugin,
    PackageOverlayPlugin,
)

pytestmark = [
    pytest.mark.usefixtures("enable_overlay_and_partitions_features"),
    pytest.mark.requires_root,
]


@pytest.fixture(autouse=True)
def register_plugins():
    """Register and unregister the test overlay plugins."""
    plugins.register(
        {
            "host-overlay": HostCommandPlugin,
            "chroot-overlay": ChrootCommandPlugin,
            "package-overlay": PackageOverlayPlugin,
        }
    )
    yield
    plugins.unregister("host-overlay", "chroot-overlay", "package-overlay")


DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    ("parts_file", "expected"),
    [
        pytest.param(
            "parts-host-only.yaml",
            {"mypart": ["host-proof.txt"]},
            id="host-only",
        ),
        pytest.param(
            "parts-chroot-only.yaml",
            {"mypart": ["chroot-proof.txt"]},
            id="chroot-only",
        ),
        pytest.param(
            "parts-host-and-chroot.yaml",
            {
                "host-part": ["host-proof.txt"],
                "chroot-part": ["chroot-proof.txt"],
            },
            id="host-and-chroot",
        ),
        pytest.param(
            "parts-package-and-chroot.yaml",
            {"mypart": ["plugin-overlay-proof.txt"]},
            id="package-and-chroot",
        ),
        pytest.param(
            "parts-override-overlay.yaml",
            {"mypart": ["chroot-proof.txt", "override-proof.txt"]},
            id="override-overlay",
        ),
        pytest.param(
            "parts-overlay-script.yaml",
            {"mypart": ["host-proof.txt", "script-proof.txt"]},
            id="overlay-script",
        ),
    ],
)
def test_plugin_overlay_commands(new_homedir_path, parts_file, expected):
    """Plugin overlay commands create expected files in the overlay layer."""
    parts = yaml.safe_load((DATA_DIR / parts_file).read_text())

    base_dir = new_homedir_path / "base"
    base_dir.mkdir()
    work_dir = new_homedir_path / "work"
    work_dir.mkdir()
    cache_dir = new_homedir_path / "cache"
    cache_dir.mkdir()

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test",
        cache_dir=cache_dir,
        work_dir=work_dir,
        partitions=["default"],
        base_layer_dir=base_dir,
        base_layer_hash=b"empty",
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    work_parts = work_dir / "parts"
    for part_name, expected_files in expected.items():
        for expected_file in expected_files:
            proof = work_parts / part_name / "layer" / expected_file
            assert proof.exists(), (
                f"{expected_file} not found in {part_name}'s overlay layer"
            )

    # Check files reached the prime directory
    prime_dir = work_dir / "prime"
    for expected_files in expected.values():
        for expected_file in expected_files:
            assert (prime_dir / expected_file).exists(), (
                f"{expected_file} not found in prime directory"
            )
