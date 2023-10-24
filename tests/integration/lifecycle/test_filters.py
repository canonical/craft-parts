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

import textwrap
from pathlib import Path

import craft_parts
import yaml
from craft_parts import Action, Step


def test_stage_prime_filtering(new_dir):
    parts_yaml = textwrap.dedent(
        """
        parts:
          my-part:
            plugin: nil
            override-build: |
              touch ${CRAFT_PART_INSTALL}/testfile
            stage:
              - testfile
            prime:
              - -*
        """
    )

    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.PRIME)
    assert actions == [
        Action("my-part", Step.PULL),
        Action("my-part", Step.BUILD),
        Action("my-part", Step.STAGE),
        Action("my-part", Step.PRIME),
    ]
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # testfile must be in stage but not in prime
    assert Path("stage/testfile").exists()
    assert Path("prime/testfile").exists() is False
