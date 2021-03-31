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

from craft_parts.actions import Action, ActionType
from craft_parts.steps import Step


def test_action_type():
    assert f"{ActionType.RUN!r}" == "ActionType.RUN"
    assert f"{ActionType.RERUN!r}" == "ActionType.RERUN"
    assert f"{ActionType.UPDATE!r}" == "ActionType.UPDATE"
    assert f"{ActionType.SKIP!r}" == "ActionType.SKIP"


def test_action_representation():
    action = Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="is tired")
    assert f"{action!r}" == "Action('foo', Step.PULL, ActionType.SKIP, 'is tired')"


def test_action_default_parameters():
    action = Action("foo", Step.PULL)
    assert action.type == ActionType.RUN
    assert action.reason is None


def test_action_properties():
    action = Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="is tired")
    assert action.part_name == "foo"
    assert action.step == Step.PULL
    assert action.type == ActionType.SKIP
    assert action.reason == "is tired"


def test_action_comparison():
    action = Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="is tired")
    a1 = Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="is tired")
    a2 = Action("bar", Step.PULL, action_type=ActionType.SKIP, reason="is tired")
    a3 = Action("foo", Step.BUILD, action_type=ActionType.SKIP, reason="is tired")
    a4 = Action("foo", Step.PULL, action_type=ActionType.RUN, reason="is tired")
    a5 = Action("foo", Step.PULL, action_type=ActionType.SKIP)
    assert action == a1
    assert action != a2
    assert action != a3
    assert action != a4
    assert action != a5
