# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import textwrap
from pathlib import Path

import yaml

from craft_parts import LifecycleManager, Step


def test_rust_plugin(new_dir, datadir):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: test_rust/simple
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lifecycle = LifecycleManager(
        parts, application_name="test_rust_plugin", cache_dir=new_dir
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


def test_rust_plugin_features(new_dir, datadir):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: test_rust/features
            rust-features: [conditional-feature-present]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lifecycle = LifecycleManager(
        parts, application_name="test_rust_plugin_features", cache_dir=new_dir
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello-features")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


def test_rust_plugin_workspace(new_dir, datadir):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: rust
            source: test_rust/workspace
            rust-path: ["hello"]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lifecycle = LifecycleManager(
        parts, application_name="test_rust_hello_workspace", cache_dir=new_dir
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "rust-hello-workspace")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"
