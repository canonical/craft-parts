# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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


def test_stage_prime_filtering(new_dir, partitions):
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
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
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


def test_stage_prime_reuse_fileset(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """
        parts:
          my-part:
            plugin: nil
            override-build: |
              touch $CRAFT_PART_INSTALL/foo
              touch $CRAFT_PART_INSTALL/qux
              touch $CRAFT_PART_INSTALL/testfile
            organize:
              "foo": baz
              "testfile": (mypart)/testfile-renamed
            stage:
              - -baz
              - '*'
              - -(mypart)/*
            override-stage: |
              craftctl default
              touch $CRAFT_STAGE/baz
        """
    )

    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir, partitions=partitions
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

    # baz must be in stage (re-added after the exclusion), but not in prime
    # excluded based via the reused fileset for prime.
    assert Path("stage/baz").exists()
    assert Path("stage/qux").exists()
    assert Path("prime/baz").exists() is False
    assert Path("prime/qux").exists()
    # testfile-renamed was moved in mypart but not staged
    assert Path("partitions/mypart/parts/my-part/install/testfile-renamed").exists()
    assert Path("partitions/mypart/prime/testfile-renamed").exists() is False
