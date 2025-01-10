# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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
"""Integration tests for parts that depend on each other."""


import os
import pathlib

import pytest
import yaml

import craft_parts


@pytest.mark.parametrize(
    "project",
    [
        "pygit2-1.13",
        # "pygit2-1.17"
    ]
)
def test_dependent_parts(new_dir, project):
    """Test building pygit2 with a dependent part that builds libgit2."""
    parts_dir = pathlib.Path(__file__).parent / project
    parts = yaml.safe_load((parts_dir / "parts.yaml").read_text())


    lf = craft_parts.LifecycleManager(
        parts, application_name="test_dependent_parts", cache_dir=new_dir,
        parallel_build_count=len(os.sched_getaffinity(0))
    )

    actions = lf.plan(craft_parts.Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert not pathlib.Path("stage/usr/include/git2.h").exists()
    assert not pathlib.Path("stage/include/git2.h").exists()
    assert pathlib.Path("backstage/include/git2.h").exists()

    lf.clean(craft_parts.Step.BUILD, part_names=["libgit2"])

    assert not pathlib.Path("backstage/include/git2.h").exists()
    #
    # with lf.action_executor() as ctx:
    #     ctx.execute(actions)
    #
    # assert pathlib.Path("backstage/include/git2.h").exists()
