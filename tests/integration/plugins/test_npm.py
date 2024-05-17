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


def test_npm_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: npm
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("hello.js").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env node

            console.log('hello world');
            """
        )
    )

    Path("package.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "npm-hello",
              "version": "1.0.0",
              "description": "Testing grounds for snapcraft integration tests",
              "bin": {
                "npm-hello": "hello.js"
              },
              "scripts": {
                "npm-hello": "echo 'Error: no test specified' && exit 1"
              },
              "author": "",
              "license": "GPL-3.0"
            }
            """
        )
    )

    Path("package-lock.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "npm-hello",
              "version": "1.0.0",
              "lockfileVersion": 1
            }
            """
        )
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_npm_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "npm-hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"

    assert Path(lifecycle.project_info.prime_dir, "bin", "node").exists() is False


def test_npm_plugin_include_node(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: npm
            source: .
            npm-include-node: True
            npm-node-version: "16.14.2"
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("hello.js").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env node

            console.log('hello world');
            """
        )
    )

    Path("package.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "npm-hello",
              "version": "1.0.0",
              "description": "Testing grounds for snapcraft integration tests",
              "bin": {
                "npm-hello": "hello.js"
              },
              "scripts": {
                "npm-hello": "echo 'Error: no test specified' && exit 1"
              },
              "author": "",
              "license": "GPL-3.0"
            }
            """
        )
    )

    Path("package-lock.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "npm-hello",
              "version": "1.0.0",
              "lockfileVersion": 1
            }
            """
        )
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_npm_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "bin", "npm-hello")
    node_path = Path(lifecycle.project_info.prime_dir, "bin", "node")
    assert node_path.exists()
    # try to use bundled Node.js to execute the script
    output = subprocess.check_output([str(node_path), str(binary)], text=True)
    assert output == "hello world\n"
