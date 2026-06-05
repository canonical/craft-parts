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

import textwrap

import craft_parts
import yaml
from craft_parts import Step

basic_parts_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        build-environment:
          - FOO: $FOO there  # modify the environment variable
        override-build: |
          echo $FOO          # print the modified content
    """
)


def test_build_environment(new_dir, capfd):
    parts = yaml.safe_load(basic_parts_yaml)

    lf_kwargs = {
        "application_name": "test_demo",
        "cache_dir": new_dir,
        "build_environment": ["FOO=hello"],
    }

    lf = craft_parts.LifecycleManager(parts, **lf_kwargs)
    actions = lf.plan(Step.BUILD)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    captured = capfd.readouterr()
    assert captured.out == "hello there\n"

