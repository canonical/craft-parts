# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [
    pytest.mark.plugin,
    # fp-compiler is not packaged for every architecture craft-parts is tested on.
    pytest.mark.skipif(
        shutil.which("fpc") is None, reason="fpc is not installed on the test host"
    ),
]

SOURCE_LOCATION = Path(__file__).parent / "test_fpc_use"


def test_fpc_use(new_dir, partitions):
    """Units and include files from an fpc-use part are found by an fpc part."""
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          greetlib:
            plugin: fpc-use
            source: {SOURCE_LOCATION / "greetlib"}
            fpc-use-unit-paths:
              - units
            fpc-use-include-paths:
              - include
          hello:
            plugin: fpc
            source: {SOURCE_LOCATION / "app"}
            fpc-programs:
              - src/hello.pas
            after:
              - greetlib
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_fpc_use",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    export_dir = Path(new_dir, "backstage", "fpc-use", "greetlib")
    assert (export_dir / "source" / "units" / "greeter.pas").is_file()
    assert (export_dir / "unit-paths").read_text() == "units\n"
    assert (export_dir / "include-paths").read_text() == "include\n"

    prime_dir = Path(lf.project_info.prime_dir)
    assert not list(prime_dir.rglob("*.pas"))

    binary = prime_dir / "bin" / "hello"
    assert binary.is_file()
    assert subprocess.check_output([str(binary)], text=True) == "Hello, world!\n"


def test_fpc_use_defaults(new_dir, partitions):
    """By default the source directory itself is the unit search path."""
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          greetlib:
            plugin: fpc-use
            source: {SOURCE_LOCATION / "flatlib"}
          hello:
            plugin: fpc
            source: {SOURCE_LOCATION / "app"}
            fpc-programs:
              - src/hello.pas
            after:
              - greetlib
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_fpc_use",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")
    assert binary.is_file()
    assert (
        subprocess.check_output([str(binary)], text=True)
        == "Hello from the flat library!\n"
    )
