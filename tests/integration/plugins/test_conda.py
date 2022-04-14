# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import os
import subprocess
import textwrap
from pathlib import Path

import yaml

from craft_parts import LifecycleManager, Step


def test_conda_plugin(new_dir):
    parts_yaml = textwrap.dedent(
        """\
        parts:
            ipython:
              plugin: conda
              conda-packages:
              - ipython
              conda-python-version: "3.9"
              conda-install-prefix: "$CRAFT_PART_INSTALL"
            hello:
              plugin: dump
              source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("hello").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env ipython3

            print('hello world')

            """
        )
    )
    Path("hello").chmod(0o755)

    lifecycle = LifecycleManager(
        parts, application_name="test_conda_plugin", cache_dir=new_dir
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    command = [str(Path(lifecycle.project_info.prime_dir, "hello"))]

    # add conda's binary path to $PATH
    env = os.environ.copy()
    env["PATH"] = f"{lifecycle.project_info.prime_dir}/bin:" + env["PATH"]

    output = subprocess.check_output(command, text=True, env=env)

    # ipython outputs a header with escape characters, so use `endswith()`
    assert output.endswith("hello world\n")
