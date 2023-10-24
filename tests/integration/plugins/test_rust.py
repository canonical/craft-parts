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

import subprocess
import textwrap
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step


def test_rust_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "rust-hello"
            version = "1.0.0"
            edition = "2021"
            """
        )
    )

    Path("src").mkdir()
    Path("src/main.rs").write_text(
        textwrap.dedent(
            """\
            fn main() {
                println!("hello world");
            }
            """
        )
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_rust_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


def test_rust_plugin_features(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: .
            rust-features: [conditional-feature-present]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "rust-hello-features"
            version = "1.0.0"
            edition = "2021"

            [features]
            conditional-feature-present = []
            conditional-feature-missing = []

            [dependencies]
            log = "*"
            """
        )
    )

    Path("src").mkdir()
    Path("src/main.rs").write_text(
        textwrap.dedent(
            """\
            extern crate log;
            fn main() {
                #[cfg(feature="conditional-feature-present")]
                println!("hello world");
            }
            """
        )
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_rust_plugin_features",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello-features")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


def test_rust_plugin_workspace(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: .
            rust-path: ["hello"]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [workspace]
            members = [
                "hello",
                "say",
            ]
            """
        )
    )

    Path("hello").mkdir()
    Path("hello/Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "rust-hello-workspace"
            version = "1.0.0"
            edition = "2021"

            [dependencies]
            say = { path = "../say" }
            """
        )
    )

    Path("hello/src").mkdir()
    Path("hello/src/main.rs").write_text(
        textwrap.dedent(
            """\
            use say;
            fn main() {
                say::hello();
            }
            """
        )
    )

    Path("say").mkdir()
    Path("say/Cargo.toml").write_text(
        textwrap.dedent(
            """\
            [package]
            name = "say"
            version = "0.1.0"
            edition = "2021"
            """
        )
    )

    Path("say/src").mkdir()
    Path("say/src/lib.rs").write_text(
        textwrap.dedent(
            """\
            pub fn hello() {
                println!("hello world");
            }
            """
        )
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_rust_hello_workspace",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello-workspace")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"
