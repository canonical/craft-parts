# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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


def test_go_plugin(new_dir, mocker):
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
        ),
        encoding="utf-8",
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
        ),
        encoding="utf-8",
    )

    # the go compiler is installed in the ci test setup
    lf = LifecycleManager(parts, application_name="test_go", cache_dir=new_dir)
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "I can eat glass and it doesn't hurt me."
