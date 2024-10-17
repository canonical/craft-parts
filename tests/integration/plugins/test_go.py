# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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


def test_go_plugin(new_dir, partitions, mocker):
    parts_yaml = textwrap.dedent(
        """
        parts:
          foo:
            plugin: go
            source: .
            go-buildtags: [my_tag]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("go.mod").write_text(
        textwrap.dedent(
            """
            module example.com/hello
            go 1.13
            require rsc.io/quote v1.5.2
            """
        )
    )

    Path("hello.go").write_text(
        textwrap.dedent(
            """
            // +build my_tag
            package main

            import "fmt"
            import "rsc.io/quote"

            func main() {
                fmt.Printf("%s", quote.Glass())
            }
            """
        )
    )

    # the go compiler is installed in the ci test setup
    lf = LifecycleManager(
        parts, application_name="test_go", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "I can eat glass and it doesn't hurt me."


def test_go_generate(new_dir, partitions):
    """Test code generation via "go generate" in parts using the go plugin

    The go code in the "test_go" dir uses "gen/generator.go" to create, at build time,
    the "main.go" file that produces the final binary.
    """
    source_location = Path(__file__).parent / "test_go"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: go
            source: {source_location}
            go-generate:
              - gen/generator.go
            build-environment:
              - GO111MODULE: "on"
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_go",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "generate")
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    # This is the expected output that "gen/generator.go" sets in "main.go"
    assert output == "This is a generated line\n"


def test_go_workspace_use(new_dir, partitions):
    source_location = Path(__file__).parent / "test_go_workspace"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          go-flags:
            source: https://github.com/jessevdk/go-flags.git
            plugin: go-use
          hello:
            after:
            - go-flags
            plugin: go
            source: {source_location}
            build-environment:
              - GO111MODULE: "on"
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_go",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "workspace")
    assert binary.is_file()

    output = subprocess.check_output([str(binary), "--say=hello"], text=True)
    assert output == "hello\n"
