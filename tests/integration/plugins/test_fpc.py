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


@pytest.mark.parametrize(
    ("parts_yaml", "binary_path", "expected_output"),
    [
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: fpc
                    source: {source_location}
                    fpc-programs:
                      - src/goodbye.pas
                """
            ),
            "bin/goodbye",
            "Goodbye, world!\n",
            id="basic",
        ),
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: fpc
                    source: {source_location}
                    fpc-programs:
                      - src/hello.pas
                    fpc-unit-paths:
                      - units
                    fpc-include-paths:
                      - include
                """
            ),
            "bin/hello",
            "Hello, world!\n",
            id="with-paths",
        ),
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: fpc
                    source: {source_location}
                    fpc-programs:
                      - src/hello.pas
                    fpc-unit-paths:
                      - units
                    fpc-include-paths:
                      - include
                    fpc-parameters:
                      - -dLOUD
                """
            ),
            "bin/hello",
            "HELLO, WORLD!\n",
            id="with-parameters",
        ),
    ],
)
def test_fpc_plugin(new_dir, partitions, parts_yaml, binary_path, expected_output):
    """Test builds with the fpc plugin."""
    source_location = Path(__file__).parent / "test_fpc"

    parts_yaml_str = parts_yaml.format(source_location=source_location)
    parts = yaml.safe_load(parts_yaml_str)

    lf = LifecycleManager(
        parts,
        application_name="test_fpc",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, binary_path)
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    assert output == expected_output


def test_fpc_plugin_multiple_programs(new_dir, partitions):
    """Each entry in fpc-programs produces one executable, and nothing else is installed."""
    source_location = Path(__file__).parent / "test_fpc"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: fpc
            source: {source_location}
            fpc-programs:
              - src/hello.pas
              - src/goodbye.pas
            fpc-unit-paths:
              - units
            fpc-include-paths:
              - include
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_fpc",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    prime_dir = Path(lf.project_info.prime_dir)
    assert sorted(p.name for p in (prime_dir / "bin").iterdir()) == [
        "goodbye",
        "hello",
    ]
    assert not list(prime_dir.rglob("*.ppu"))

    unit_dir = Path(lf.project_info.parts_dir, "foo", "build", ".parts", "units")
    assert (unit_dir / "greeter.ppu").is_file()
