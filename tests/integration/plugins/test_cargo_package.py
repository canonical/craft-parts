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

import pathlib
import subprocess
import textwrap
from typing import cast

import pytest
import yaml
from craft_parts import LifecycleManager, Step
from craft_parts.errors import PluginBuildError

CARGO_PARTS_YAML = f"""\
parts:
  rust-ascii:
    plugin: cargo-package
    source: https://github.com/tomprogrammer/rust-ascii.git
    source-tag: v0.8.7  # Intentionally get a very old version of ascii to test
    # Use the system's cargo, not cargo from the snap.
    cargo-package-cargo-command: /usr/bin/cargo
  ascii-consumer:  # Test that we can correctly consume the package from another part.
    after: [rust-ascii]
    plugin: rust
    source: {pathlib.Path(__file__).parent / "test_cargo_package"}
    rust-channel: none
    build-environment:
      # Should not be necessary as the other part sets offline, but do so anyway
      # so we don't use an online version if we change this.
      - CARGO_NET_OFFLINE: "true"
      # Not necessary as the other part overrides crates.io, but override it anyway
      # to ensure forward compatibility.
      - CARGO_REGISTRY_DEFAULT: "craft-parts"
      # Don't use snaps first.
      - PATH: /usr/bin:$PATH
"""

BROKEN_CARGO_PARTS_YAML = f"""\
parts:
  rust-ascii:
    plugin: cargo-package
    source: https://github.com/tomprogrammer/rust-ascii.git
    source-tag: v1.1.0  # This will work, but the consumer will break because it wants an old version.
    # Use the system's cargo, not cargo from the snap.
    cargo-package-cargo-command: /usr/bin/cargo
  ascii-consumer:  # Test that we can correctly consume the package from another part.
    after: [rust-ascii]
    plugin: rust
    source: {pathlib.Path(__file__).parent / "test_cargo_package"}
    rust-channel: none
    build-environment:
      # Should not be necessary as the other part sets offline, but do so anyway
      # so we don't use an online version if we change this.
      - CARGO_NET_OFFLINE: "true"
      # Not necessary as the other part overrides crates.io, but override it anyway
      # to ensure forward compatibility.
      - CARGO_REGISTRY_DEFAULT: "craft-parts"
      # Don't use snaps first.
      - PATH: /usr/bin:$PATH
"""


@pytest.fixture(autouse=True)
def fake_homedir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Use a temporary path as the fake home directory."""
    monkeypatch.setenv("HOME", tmp_path.as_posix())
    return tmp_path


def test_cargo_package_plugin_goes_to_backstage(new_path, partitions):
    parts = yaml.safe_load((pathlib.Path(__file__).parent / "test_cargo_package/parts.yaml").read_text())

    lifecycle = LifecycleManager(
        parts,
        application_name="test_cargo_package_plugin",
        cache_dir=new_path.as_posix(),
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.BUILD, part_names=["root"])

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    # Nothing in the backstage yet
    assert list(lifecycle.project_info.backstage_dir.rglob("*")) == []
    # But we have stuff to export.
    assert (new_path / "parts/root/export/cargo_registry/ascii-1.1.0/.cargo-checksum.json").exists()

    actions = lifecycle.plan(Step.STAGE)
    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    # Nothing staged
    assert list(lifecycle.project_info.stage_dir.rglob("*")) == []
    # But we do have stuff on the backstage
    assert (new_path / "backstage/cargo_registry/ascii-1.1.0/Cargo.toml").exists()


def test_cargo_package_plugin_with_rust_consumer(new_dir, partitions):
    parts = yaml.safe_load(CARGO_PARTS_YAML)

    lifecycle = LifecycleManager(
        parts,
        application_name="test_cargo_package_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = pathlib.Path(lifecycle.project_info.prime_dir, "bin", "package-test")

    output = subprocess.run([str(binary)], text=True, capture_output=True, check=True)
    assert output.stdout == "Hello, world!\n"

    binary_contents = binary.read_bytes()
    assert b"AsciiString" in binary_contents, "binary does not reference AsciiString"


def test_cargo_package_plugin_with_wrong_version(new_dir, partitions):
    parts = yaml.safe_load(BROKEN_CARGO_PARTS_YAML)

    lifecycle = LifecycleManager(
        parts,
        application_name="test_cargo_package_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.STAGE, part_names=["rust-ascii"])

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    actions = lifecycle.plan(Step.STAGE, part_names=["ascii-consumer"])

    with lifecycle.action_executor() as ctx:
        with pytest.raises(PluginBuildError) as exc_info:
            ctx.execute(actions)

    err = cast(bytes, exc_info.value.stderr)

    assert b'failed to select a version for the requirement `ascii = "^0.8.7"`' in err
    assert b"candidate versions found which didn't match: 1.1.0" in err

