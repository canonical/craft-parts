# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

import pytest
import yaml

from craft_parts import LifecycleManager, Step


def test_bazel_plugin_with_bazel_deps(new_dir, partitions):
    # Set up a minimal Bazel project
    source_dir = Path(__file__).parent / "test_bazel"
    source_dir.mkdir(exist_ok=True)
    (source_dir / "main.cc").write_text(
        textwrap.dedent(
            """
            #include <iostream>
            int main() {
                std::cout << "Hello from Bazel!" << std::endl;
                return 0;
            }
            """
        )
    )
    (source_dir / "BUILD").write_text(
        textwrap.dedent(
            """
            cc_binary(
                name = "hello_bazel",
                srcs = ["main.cc"],
            )
            """
        )
    )
    (source_dir / "MODULE.bazel").write_text(
        textwrap.dedent(
            """
            module(
                name = "test_bazel_module",
                version = "0.1.0",
            )
            """
        )
    )

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          bazel-deps:
            plugin: nil
            override-build: |
              curl -L -o $CRAFT_PART_INSTALL/bazelisk https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-amd64
              chmod +x $CRAFT_PART_INSTALL/bazelisk
              ln -sf $CRAFT_PART_INSTALL/bazelisk $CRAFT_PART_INSTALL/bazel
            stage:
              - bazel
              - bazelisk
          foo:
            plugin: bazel
            source: {source_dir}
            after: [bazel-deps]
            bazel-targets: [//:hello_bazel]
            build-environment:
              - PATH: $CRAFT_STAGE:$PATH
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_bazel",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Bazel output binaries are typically in bazel-bin/hello_bazel
    bazel_bin_dir = source_dir / "bazel-bin"
    binary = bazel_bin_dir / "hello_bazel"
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    assert output.strip() == "Hello from Bazel!"