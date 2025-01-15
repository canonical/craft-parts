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

import pytest
import yaml
from craft_parts import LifecycleManager, Step

CARGO_PARTS_YAML = """\
parts:
  rust-ascii:
    plugin: cargo-package
    source: https://github.com/tomprogrammer/rust-ascii.git
    source-tag: v0.8.7  # Intentionally get a very old version of ascii to test
  ascii-consumer:  # Test that we can correctly consume the package from another part.
    after: [rust-ascii]
    plugin: rust
    source: .
    rust-channel: none
    build-environment:
      # Should not be necessary as the other part sets offline, but do so anyway
      # so we don't use an online version if we change this.
      - CARGO_NET_OFFLINE: "true"
      # Not necessary as the other part overrides crates.io, but override it anyway
      # to ensure forward compatibility.
      - CARGO_REGISTRY_DEFAULT: "craft-parts"
"""


@pytest.fixture(autouse=True)
def fake_homedir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> pathlib.Path:
    """Use a temporary path as the fake home directory."""
    monkeypatch.setenv("HOME", tmp_path.as_posix())
    return tmp_path


def test_cargo_package_plugin_with_rust_consumer(new_dir, partitions):
    parts = yaml.safe_load(CARGO_PARTS_YAML)

    (new_dir / "Cargo.toml").write_text(
        textwrap.dedent(
            """\
                [package]
                name = "package-test"
                version = "0.1.0"
                edition = "2021"

                [dependencies]
                ascii = "0.8.7"
            """
        ),
        encoding="utf-8",
    )
    (new_dir / "src").mkdir()
    (new_dir / "src" / "main.rs").write_text(
        textwrap.dedent(
            """\
                use ascii::{AsciiString};
                fn main() {
                    let my_str = match AsciiString::from_ascii("Hello, world!") {
                        Ok(my_str) => my_str,
                        Err(_) => todo!(),
                    };
                    println!("{}", my_str);
                }
            """
        ),
        encoding="utf-8",
    )

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
