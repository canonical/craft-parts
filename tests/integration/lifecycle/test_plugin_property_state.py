# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
from typing import Literal

import craft_parts
import pytest
import yaml
from craft_parts import Action, ActionType, Part, Step, plugins
from craft_parts.state_manager import states
from overrides import override


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


class ExamplePluginProperties(plugins.PluginProperties, frozen=True):
    """The application-defined plugin properties."""

    plugin: Literal["example"] = "example"

    example_property: int | None


class ExamplePlugin(plugins.Plugin):
    """Our application plugin."""

    properties_class = ExamplePluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        return []


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME])
def test_plugin_property_state(new_dir, step):
    plugins.register({"example": ExamplePlugin})

    data = yaml.safe_load(
        textwrap.dedent(
            """\
            parts:
              foo:
                plugin: example
                example-property: 42
            """
        )
    )

    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )

    # build parts
    actions = lcm.plan(Step.PRIME)
    with lcm.action_executor() as aex:
        aex.execute(actions)

    # check if state file contains the plugin property
    part = Part("foo", {"plugin": "example"})
    state = states.load_step_state(part, step)
    assert state is not None
    assert state.part_properties["example-property"] == 42


def test_plugin_property_build_dirty(new_dir):
    plugins.register({"example": ExamplePlugin})

    data = yaml.safe_load(
        textwrap.dedent(
            """\
            parts:
              foo:
                plugin: example
                example-property: 42
            """
        )
    )

    # build parts
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    with lcm.action_executor() as aex:
        aex.execute(actions)

    # run again, verify that all actions are skipped
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    assert actions == [
        Action("foo", Step.PULL, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PRIME, ActionType.SKIP, reason="already ran"),
    ]

    # change the plugin property and run again, it reruns from build
    data["parts"]["foo"]["example-property"] = 43
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    assert actions == [
        Action("foo", Step.PULL, ActionType.SKIP, reason="already ran"),
        Action(
            "foo",
            Step.BUILD,
            ActionType.RERUN,
            reason="'example-property' property changed",
        ),
        Action("foo", Step.STAGE),
        Action("foo", Step.PRIME),
    ]


class Example2PluginProperties(plugins.PluginProperties, frozen=True):
    """The application-defined plugin properties."""

    example_property: int | None

    @classmethod
    @override
    def get_pull_properties(cls) -> list[str]:
        return ["example-property"]


class Example2Plugin(plugins.Plugin):
    """Another application plugin."""

    properties_class = Example2PluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        return []


def test_plugin_property_pull_dirty(new_dir):
    plugins.register({"example": Example2Plugin})

    data = yaml.safe_load(
        textwrap.dedent(
            """\
            parts:
              foo:
                plugin: example
                example-property: 42
            """
        )
    )

    # build parts
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    with lcm.action_executor() as aex:
        aex.execute(actions)

    # run again, verify that all actions are skipped
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    assert actions == [
        Action("foo", Step.PULL, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.BUILD, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.STAGE, ActionType.SKIP, reason="already ran"),
        Action("foo", Step.PRIME, ActionType.SKIP, reason="already ran"),
    ]

    # change the plugin property and run again, it reruns from pull
    data["parts"]["foo"]["example-property"] = 43
    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )
    actions = lcm.plan(Step.PRIME)
    assert actions == [
        Action(
            "foo",
            Step.PULL,
            ActionType.RERUN,
            reason="'example-property' property changed",
        ),
        Action("foo", Step.BUILD),
        Action("foo", Step.STAGE),
        Action("foo", Step.PRIME),
    ]
