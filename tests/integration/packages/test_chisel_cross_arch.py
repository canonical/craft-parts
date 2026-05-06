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
"""Integration tests for staging chisel slices with a target architecture."""

import subprocess
from pathlib import Path

import pytest
from craft_parts.packages import deb
from craft_parts.utils import os_utils

# Architectures supported by chisel and craft-parts, mapped to their expected
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

# These are the Ubuntu versions that Chisel currently supports.
SUPPORTED_UBUNTU_VERSIONS = frozenset(
    {"20.04", "22.04", "22.10", "24.04", "24.10", "25.04", "25.10", "26.04"}
)


def _current_release_supported() -> bool:
    """Whether Chisel supports the current running OS release."""
    release = os_utils.OsRelease()
    return (
        release.id() == "ubuntu" and release.version_id() in SUPPORTED_UBUNTU_VERSIONS
    )


@pytest.mark.skipif(
    not _current_release_supported(), reason="Test needs Chisel support"
)
@pytest.mark.flaky(reruns=3, only_rerun="ChiselError", reason="Fails on network issues")
@pytest.mark.parametrize(
    ("arch", "triplet"),
    _ARCH_TO_TRIPLET.items(),
    ids=_ARCH_TO_TRIPLET.keys(),
)
def test_chisel_slices_target_arch(
    new_homedir_path: Path, arch: str, triplet: str
) -> None:
    """Verify that chisel cuts slices for the specified target architecture.

    The libc6_libs slice installs shared libraries into /usr/lib/<triplet>/,
    so we can verify the correct architecture was used by checking which
    triplet directory is populated.
    """
    install_path = new_homedir_path / "install"
    install_path.mkdir()

    deb.Ubuntu.unpack_stage_packages(
        stage_packages_path=Path("unused"),
        install_path=install_path,
        stage_packages=["libc6_libs"],
        arch=arch,
    )

    # The libc6 libraries are under the arch-specific triplet path.
    # On usrmerge systems (22.04+) they're in /usr/lib/<triplet>/,
    # on pre-usrmerge (20.04) they're in /lib/<triplet>/.
    usr_triplet_dir = install_path / "usr" / "lib" / triplet
    lib_triplet_dir = install_path / "lib" / triplet

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
        f"Install contents: {list(install_path.rglob('*'))[:40]}"
    )

    # Verify the ld.so is an ELF binary for the correct architecture
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
        for prefix in (install_path / "usr" / "lib", install_path / "lib"):
            other_dir = prefix / other_triplet
            assert not other_dir.exists(), (
                f"Unexpected triplet directory for {other_arch} found "
                f"when building for {arch}"
            )
