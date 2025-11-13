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


@pytest.mark.parametrize(
    ("parts_yaml", "binary_path", "expected_output"),
    [
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: make
                    source: {source_location}
                """
            ),
            "bin/hello",
            "Hello, world!\n",
            id="basic",
        ),
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: make
                    source: {source_location}
                    make-parameters:
                      - MESSAGE=Greetings
                      - TARGET=craft-parts
                """
            ),
            "bin/hello",
            "Greetings, craft-parts!\n",
            id="with-parameters",
        ),
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  tree:
                    plugin: make
                    source: https://github.com/Old-Man-Programmer/tree.git
                    source-type: git
                    source-tag: "2.2.1"
                    override-build: |
                      make -j"${{CRAFT_PARALLEL_BUILD_COUNT}}"
                      mkdir -p "${{CRAFT_PART_INSTALL}}/bin"
                      cp tree "${{CRAFT_PART_INSTALL}}/bin/"
                """
            ),
            "bin/tree",
            "tree v2.2.1",
            id="real-project",
        ),
    ],
)
def test_make_plugin(new_dir, partitions, parts_yaml, binary_path, expected_output):
    """Test builds with the make plugin."""
    source_location = Path(__file__).parent / "test_make"

    parts_yaml_str = parts_yaml.format(source_location=source_location)
    parts = yaml.safe_load(parts_yaml_str)

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

    binary = Path(lf.project_info.prime_dir, binary_path)
    assert binary.is_file()

    # For the real project test, check version output; for others, check exact output
    if "tree v" in expected_output:
        output = subprocess.check_output([str(binary), "--version"], text=True)
        assert expected_output in output
    else:
        output = subprocess.check_output([str(binary)], text=True)
        assert output == expected_output
