# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import re
import subprocess
import textwrap

import pytest
import yaml
from craft_parts import LifecycleManager, Step


@pytest.fixture(scope="module")
def go_version():
    output = subprocess.run(
        ["go", "version"], check=True, capture_output=True
    ).stdout.decode()
    match = re.match(r"go version go([\d.]+)", output)
    if match is None:
        raise RuntimeError("Cannot determine go version")
    return match.group(1)


def test_go_workspace_use(new_dir, partitions, go_version):
    parts_yaml = textwrap.dedent(
        """
        parts:
          go-flags:
            source: https://github.com/jessevdk/go-flags.git
            plugin: go-use
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_go",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert (new_dir / "backstage" / "go-use" / "go-flags").exists()


def test_go_workspace_use_multiple(new_dir, partitions, go_version):
    parts_yaml = textwrap.dedent(
        """
        parts:
          go-flags:
            source: https://github.com/jessevdk/go-flags.git
            plugin: go-use
          go-starlark:
            source: https://github.com/google/starlark-go.git
            plugin: go-use
            after: [go-flags]
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_go",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert (new_dir / "backstage" / "go-use" / "go-flags").exists()
    assert (new_dir / "backstage" / "go-use" / "go-starlark").exists()
