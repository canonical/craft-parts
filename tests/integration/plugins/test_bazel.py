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

pytestmark = [pytest.mark.plugin]


@pytest.mark.parametrize(
    ("parts_yaml", "binary_path", "expected_output"),
    [
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: bazel
                    source: {source_location}
                    bazel-targets:
                      - //:hello
                """
            ),
            "hello",
            "Hello, world!\n",
            id="basic",
        ),
        pytest.param(
            textwrap.dedent(
                """
                parts:
                  foo:
                    plugin: bazel
                    source: {source_location}
                    bazel-targets:
                      - //:hello
                    bazel-parameters:
                      - --compilation_mode=fastbuild
                """
            ),
            "hello",
            "Hello, world!\n",
            id="with-parameters",
        ),
    ],
)
def test_bazel_plugin(new_dir, partitions, parts_yaml, binary_path, expected_output):
    """Test builds with the bazel plugin."""
    if shutil.which("bazel") is None:
        pytest.skip("bazel is not installed on the test host")

    source_location = Path(__file__).parent / "test_bazel"
    (source_location / "hello.sh").chmod(0o755)

    parts_yaml_str = parts_yaml.format(source_location=source_location)
    parts = yaml.safe_load(parts_yaml_str)

    lf = LifecycleManager(
        parts,
        application_name="test_bazel",
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
