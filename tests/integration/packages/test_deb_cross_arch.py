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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Integration tests for staging deb packages with a target architecture."""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step
from craft_parts.packages import deb as deb_pkg
from craft_parts.utils import os_utils

# Architectures supported by craft-parts, mapped to their expected
# GNU triplet directory name under /usr/lib/.
_ARCH_TO_TRIPLET = {
    "amd64": "x86_64-linux-gnu",
    "arm64": "aarch64-linux-gnu",
    "armhf": "arm-linux-gnueabihf",
    "i386": "i386-linux-gnu",
    "ppc64el": "powerpc64le-linux-gnu",
    "riscv64": "riscv64-linux-gnu",
    "s390x": "s390x-linux-gnu",
}

# Strings that the `file` command reports for each architecture's ELF binaries.
# Some architectures have multiple possible strings depending on Ubuntu version.
_ARCH_TO_ELF_MACHINE: dict[str, str | tuple[str, ...]] = {
    "amd64": "x86-64",
    "arm64": "ARM aarch64",
    "armhf": "ARM, EABI5",
    "i386": ("Intel 80386", "Intel i386"),
    "ppc64el": "64-bit PowerPC or cisco 7500",
    "riscv64": "UCB RISC-V",
    "s390x": "IBM S/390",
}


def _is_ubuntu() -> bool:
    """Whether the current OS is Ubuntu."""
    release = os_utils.OsRelease()
    return release.id() == "ubuntu"


@pytest.fixture(autouse=True)
def _clean_cross_build_state():
    """Remove foreign architectures and cross-build sources after each test.

    Each test adds a foreign architecture via ``dpkg --add-architecture`` and
    writes APT source files.  Without cleanup the next test inherits stale
    state, causing APT failures when there are registered foreign architectures
    with no matching sources.
    """
    # Record the foreign architectures *before* the test.
    before = set(
        subprocess.check_output(
            ["dpkg", "--print-foreign-architectures"], text=True
        ).split()
    )

    yield

    # Remove any foreign architectures added during the test.
    after = set(
        subprocess.check_output(
            ["dpkg", "--print-foreign-architectures"], text=True
        ).split()
    )
    for arch in after - before:
        subprocess.run(
            ["dpkg", "--remove-architecture", arch],
            check=False,
        )

    # Remove cross-build sources file added by the executor.
    cross_sources = Path("/etc/apt/sources.list.d/craft-parts-cross-build.sources")
    cross_sources.unlink(missing_ok=True)

    # Clear the refresh_packages_list lru_cache so the next test gets a
    # fresh APT state.
    deb_pkg.Ubuntu.refresh_packages_list.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.skipif(not _is_ubuntu(), reason="Test needs Ubuntu with APT")
@pytest.mark.skipif(os.getenv("CI") != "true", reason="Test only runs in CI")
@pytest.mark.skipif(os.geteuid() != 0, reason="Test requires root")
@pytest.mark.flaky(
    reruns=3, only_rerun="PackageNotFound", reason="Fails on network issues"
)
@pytest.mark.parametrize(
    ("arch", "triplet"),
    _ARCH_TO_TRIPLET.items(),
    ids=_ARCH_TO_TRIPLET.keys(),
)
def test_stage_packages_target_arch(
    new_homedir_path: Path, arch: str, triplet: str, partitions
) -> None:
    """Verify that deb stage packages are fetched and unpacked for the target arch.

    Uses libc6 as a test package since it installs architecture-specific shared
    libraries into /usr/lib/<triplet>/.
    """
    parts_yaml = textwrap.dedent(
        """\
        parts:
          test-part:
            plugin: nil
            stage-packages: [libc6]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_cross_deb",
        cache_dir=new_homedir_path,
        work_dir=new_homedir_path,
        arch=arch,
        partitions=partitions,
        native_cross_builds=True,
    )

    actions = lf.plan(Step.STAGE)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    stage_dir = Path(new_homedir_path) / "stage"

    # The libc6 libraries are under the arch-specific triplet path.
    # On usrmerge systems (22.04+) they're in /usr/lib/<triplet>/,
    # on pre-usrmerge (20.04) they're in /lib/<triplet>/.
    usr_triplet_dir = stage_dir / "usr" / "lib" / triplet
    lib_triplet_dir = stage_dir / "lib" / triplet

    # Find the directory that actually contains libc shared objects.
    triplet_lib_dir = None
    for candidate in (usr_triplet_dir, lib_triplet_dir):
        if candidate.is_dir() and (
            list(candidate.glob("libc.so.*")) or list(candidate.glob("libc-*.so"))
        ):
            triplet_lib_dir = candidate
            break
    assert triplet_lib_dir is not None, (
        f"Expected libc libraries for {arch} ({triplet}) not found in "
        f"either usr/lib or lib. "
        f"Stage contents: {list(stage_dir.rglob('*'))[:40]}"
    )

    # Verify ld.so is an ELF binary for the correct architecture.
    ld_so_files = list(triplet_lib_dir.glob("ld*.so.*")) or list(
        triplet_lib_dir.glob("ld-*.so")
    )
    assert ld_so_files, (
        f"No ld*.so.* found in {triplet_lib_dir}. "
        f"Contents: {list(triplet_lib_dir.iterdir())}"
    )
    file_output = subprocess.check_output(
        ["file", "-L", str(ld_so_files[0])], text=True
    )
    expected_machine = _ARCH_TO_ELF_MACHINE[arch]
    if isinstance(expected_machine, tuple):
        assert any(m in file_output for m in expected_machine), (
            f"ELF binary {ld_so_files[0].name} is not for {arch}. "
            f"Expected one of {expected_machine} in file output: {file_output}"
        )
    else:
        assert expected_machine in file_output, (
            f"ELF binary {ld_so_files[0].name} is not for {arch}. "
            f"Expected '{expected_machine}' in file output: {file_output}"
        )

    # Verify no OTHER architecture's triplet directory was populated
    for other_arch, other_triplet in _ARCH_TO_TRIPLET.items():
        if other_arch == arch:
            continue
        for prefix in (stage_dir / "usr" / "lib", stage_dir / "lib"):
            other_dir = prefix / other_triplet
            assert not other_dir.exists(), (
                f"Unexpected triplet directory for {other_arch} found "
                f"when building for {arch}"
            )
