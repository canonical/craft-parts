# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import textwrap

import yaml

import craft_parts
from craft_parts import Action, ActionType, Step

parts_yaml = textwrap.dedent(
    """\
    parts:
      bar:
        after: [foo]
        plugin: nil

      foo:
        plugin: nil
        source: a.tar.gz

      foobar:
        plugin: nil"""
)


def test_actions_simple(new_dir, mocker):
    parts = yaml.safe_load(parts_yaml)

    # first run
    # command: pull
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.PULL)
    assert actions == [
        Action("foo", Step.PULL),
        Action("bar", Step.PULL),
        Action("foobar", Step.PULL),
    ]

    # foobar part depends on nothing
    # command: prime foobar
    lf = craft_parts.LifecycleManager(parts, application_name="test_demo")
    actions = lf.plan(Step.PRIME, ["foobar"])
    assert actions == [
        # FIXME: this will be skipped after the executor writes state to disk
        # Action("foobar", Step.PULL, action_type=ActionType.SKIP, reason="already ran"),
        Action("foobar", Step.PULL, action_type=ActionType.RUN, reason=None),
        Action("foobar", Step.BUILD),
        Action("foobar", Step.STAGE),
        Action("foobar", Step.PRIME),
    ]
