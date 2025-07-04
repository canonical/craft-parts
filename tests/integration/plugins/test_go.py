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

import pytest
import yaml
from craft_parts import LifecycleManager, Step
from craft_parts.errors import PluginBuildError


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


def test_go_use(new_dir, partitions):
    # Ensure we're not using cached sources
    source_location = Path(__file__).parent / "test_go_workspace"

    (new_dir / "go-cache").mkdir()

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          sys:
            source: https://go.googlesource.com/sys
            source-type: git
            plugin: go-use
          go-flags:
            source: https://github.com/jessevdk/go-flags.git
            plugin: go-use
            source-tag: v1.6.1
            build-environment:
              - GOPROXY: "off"
          hello:
            after:
            - go-flags
            - sys
            plugin: go
            source: {source_location}
            build-environment:
              - GO111MODULE: "on"
              - GOPROXY: "off"
              - GOFLAGS: "-json"
              - GOMODCACHE: {new_dir / "go-cache"}
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


@pytest.mark.parametrize(
    "parts_yaml_template",
    [
        textwrap.dedent(
            """\
            parts:
              # Intentionally missing the part for the sys package
              go-flags:
                source: https://github.com/jessevdk/go-flags.git
                plugin: go-use
                source-tag: v1.6.1
                build-environment:
                - GOPROXY: "off"
              hello:
                after:
                - go-flags
                plugin: go
                source: {source_location}
                build-environment:
                - GO111MODULE: "on"
                - GOPROXY: "off"
                - GOFLAGS: "-json"
                - GOMODCACHE: {go_cache}
            """
        ),
        textwrap.dedent(
            """\
            parts:
              sys:
                source: https://go.googlesource.com/sys
                source-type: git
                plugin: go-use
              go-flags:
                source: https://github.com/jessevdk/go-flags.git
                plugin: go-use
                source-tag: v1.6.1
                build-environment:
                - GOPROXY: "off"
              hello:
                after:
                # Intentionally missing sys dependency
                - go-flags
                plugin: go
                source: {source_location}
                build-environment:
                - GO111MODULE: "on"
                - GOPROXY: "off"
                - GOFLAGS: "-json"
                - GOMODCACHE: {go_cache}
            """
        ),
    ],
)
def test_go_use_incomplete_parts(new_dir, partitions, parts_yaml_template: str):
    # Ensure we're not using cached sources
    source_location = Path(__file__).parent / "test_go_workspace"

    go_cache = new_dir / "go-cache"
    go_cache.mkdir()

    parts_yaml = parts_yaml_template.format(
        source_location=source_location, go_cache=go_cache
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
        with pytest.raises(PluginBuildError):
            ctx.execute(actions)
