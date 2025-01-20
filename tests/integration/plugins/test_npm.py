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

import pytest
import yaml
from craft_parts import LifecycleManager, Step
from craft_parts.plugins.base import Package


@pytest.fixture
def create_fake_package_with_node():
    def _create_fake_package_with_node():
        parts_yaml = """\
            parts:
              foo:
                plugin: npm
                source: .
                npm-include-node: True
                npm-node-version: "16.14.2"
            """
        parts_yaml = textwrap.dedent(parts_yaml)
        print(parts_yaml)

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
        return parts

    return _create_fake_package_with_node


def _paths_relative_to_install_dir(pkg_files_abs, part_install_dir):
    """Takes an iterable of Paths and chops off everything before and including
    the "install" directory, returning these transformed paths as strings in a set.
    """
    return {
        f.as_posix().partition(part_install_dir.as_posix() + "/")[2]
        for f in pkg_files_abs
    }


def _paths_relative_to_parent_modules_dir(pkg_files_abs):
    """Takes an iterable of Paths and chops off everything before and including
    the deepest "node_modules" directory, returning these transformed paths as strings
    in a set.
    """
    return {f.as_posix().rpartition("/node_modules/")[2] for f in pkg_files_abs}


def test_npm_plugin(create_fake_package_with_node, new_dir, partitions):
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


def test_npm_plugin_include_node(create_fake_package_with_node, new_dir, partitions):
    parts = create_fake_package_with_node()
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


@pytest.mark.slow
def test_npm_plugin_get_package_files(
    create_fake_package_with_node, new_dir, partitions
):
    parts = create_fake_package_with_node()
    lifecycle = LifecycleManager(
        parts,
        application_name="test_npm_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.BUILD)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    part_name = list(parts["parts"].keys())[0]
    actual_file_list = lifecycle._executor._handler[
        part_name
    ]._plugin.get_package_files()
    part_install_dir = lifecycle._executor._part_list[0].part_install_dir

    # This example bundles in node, which brings a ton of other dependencies -
    # this is perfect for checking all sorts of weird behavior.

    seeking_packages = {
        "npm-hello": False,
        "npm": False,
    }
    for pkg, pkg_files in actual_file_list.items():
        # Check for the files from our little fake package
        if pkg.name == "npm-hello":
            assert _paths_relative_to_install_dir(pkg_files, part_install_dir) == {
                "bin/npm-hello",
                "lib/node_modules/npm-hello/hello.js",
                "lib/node_modules/npm-hello/package.json",
            }

        # Verify bins were installed properly
        if pkg.name == "npm":
            pkg_files_rerooted = _paths_relative_to_install_dir(
                pkg_files, part_install_dir
            )
            assert "bin/npm" in pkg_files_rerooted
            assert "bin/npx" in pkg_files_rerooted

        if pkg.name in seeking_packages:
            seeking_packages[pkg.name] = True

    sought_collapsed = set(seeking_packages.values())
    success = len(sought_collapsed) == 1 and sought_collapsed.pop()
    assert success, f"Didn't find one or more packages: {seeking_packages}"

    # Node itself depends on four different versions of this ansi-regex
    # package. npm itself directly depends on 2.1.1, and two of npm's
    # dependencies (cli-columns and gauge) both depend on 5.0.1, which means
    # their files get collapsed under a single key (which doesn't matter for
    # our purposes.)
    ar211 = Package("npm", "ansi-regex", "2.1.1")
    assert ar211 in actual_file_list
    assert len(actual_file_list[ar211]) == 4, ar211
    assert _paths_relative_to_install_dir(
        actual_file_list[ar211], part_install_dir
    ) == {
        "lib/node_modules/npm/node_modules/ansi-regex/index.js",
        "lib/node_modules/npm/node_modules/ansi-regex/license",
        "lib/node_modules/npm/node_modules/ansi-regex/package.json",
        "lib/node_modules/npm/node_modules/ansi-regex/readme.md",
    }

    ar300 = Package("npm", "ansi-regex", "3.0.0")
    assert ar300 in actual_file_list
    assert len(actual_file_list[ar300]) == 4, ar300

    # Added "index.d.ts" file, absent from previous versions
    ar500 = Package("npm", "ansi-regex", "5.0.0")
    assert ar500 in actual_file_list
    assert len(actual_file_list[ar500]) == 5, ar500

    # Between 5.0.0 and 5.0.1 they seem to have stopped packaging the readme;
    # back to 4 files per install, and there are two installs of this version.
    ar501 = Package("npm", "ansi-regex", "5.0.1")
    assert ar501 in actual_file_list
    assert len(actual_file_list[ar501]) == 8, ar501
    assert _paths_relative_to_parent_modules_dir(actual_file_list[ar501]) == {
        "ansi-regex/index.js",
        "ansi-regex/index.d.ts",
        "ansi-regex/license",
        "ansi-regex/package.json",
    }

    # Verify scoped names work properly:
    assert (
        Package("npm", "@npmcli/installed-package-contents", "1.0.7")
        in actual_file_list
    )
    assert Package("npm", "@tootallnate/once", "1.1.2") in actual_file_list
    assert Package("npm", "@tootallnate/once", "2.0.0") in actual_file_list
