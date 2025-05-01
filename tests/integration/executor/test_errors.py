# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors


def test_plugin_build_errors(new_dir, partitions):
    """Code errors return a doc_slug and a useful message."""
    parts_yaml = textwrap.dedent(
        """
        parts:
          foo:
            plugin: go
            source: .
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
            package main

            import "fmt"
            import "rsc.io/quote"

            func main() {
                // Typo is on purpose!!
                fmt.Printfs("%s", quote.Glass())
            }
            """
        )
    )

    # the go compiler is installed in the ci test setup
    lf = LifecycleManager(
        parts, application_name="test_go", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.BUILD)

    with pytest.raises(errors.PluginBuildError) as raised:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    assert str(raised.value) == textwrap.dedent(
        """\
            Failed to run the build script for part 'foo'.

            :: + go mod download all
            :: + go install -p 1 ./...
            :: # example.com/hello
            :: ./hello.go:9:9: undefined: fmt.Printfs
            Check the build output and verify the project can work with the 'go' plugin."""
    )
    assert raised.value.doc_slug == "/reference/plugins/"
