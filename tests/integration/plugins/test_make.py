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

pytestmark = [pytest.mark.plugin]


def test_make_plugin(new_dir, partitions):
    """Test builds with the make plugin."""
    source_location = Path(__file__).parent / "test_make"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: make
            source: {source_location}
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_make",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "Hello, world!\n"


def test_make_plugin_with_parameters(new_dir, partitions):
    """Test make plugin with make-parameters."""
    source_location = Path(__file__).parent / "test_make"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: make
            source: {source_location}
            make-parameters:
              - MESSAGE=Greetings
              - TARGET=craft-parts
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_make",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    # The output "Greetings, craft-parts!" verifies that make-parameters were forwarded correctly.
    assert output == "Greetings, craft-parts!\n"


def test_make_plugin_with_real_project(new_dir, partitions):
    """Test make plugin with a real-world project (tree utility)."""
    parts_yaml = textwrap.dedent(
        """
        parts:
          tree:
            plugin: make
            source: https://github.com/Old-Man-Programmer/tree.git
            source-type: git
            source-tag: "2.2.1"
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_make",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # The tree utility's Makefile installs to $(DESTDIR)/$(TREE_DEST)
    # where TREE_DEST=tree, so the binary ends up at prime_dir/tree
    binary = Path(lf.project_info.prime_dir, "tree")
    assert binary.is_file()

    # Run tree --version to verify it works
    output = subprocess.check_output([str(binary), "--version"], text=True)
    assert "tree v2.2.1" in output
