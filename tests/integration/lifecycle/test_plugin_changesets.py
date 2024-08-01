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
from typing import Literal

import craft_parts
import yaml
from craft_parts import Action, ActionProperties, ActionType, Step, plugins


def setup_function():
    plugins.unregister_all()


def teardown_module():
    plugins.unregister_all()


class ExamplePluginProperties(plugins.PluginProperties, frozen=True):
    """The application-defined plugin properties."""

    plugin: Literal["example"] = "example"


class ExamplePlugin(plugins.Plugin):
    """Our application plugin."""

    properties_class = ExamplePluginProperties

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        if self._action_properties.changed_files:
            return [f"echo Changed files: {self._action_properties.changed_files}"]

        return ["echo no files changed"]


def test_changesets(new_dir, mocker, capfd):
    plugins.register({"example": ExamplePlugin})

    Path("dir1").mkdir()
    Path("dir1/foo").touch()

    data = yaml.safe_load(
        textwrap.dedent(
            """\
            parts:
              foo:
                plugin: example
                source: dir1
            """
        )
    )

    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )

    # build parts

    actions = lcm.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.BUILD),
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    assert capfd.readouterr().out == "no files changed\n"

    # just repull

    actions = lcm.plan(Step.PULL)
    assert actions == [
        Action("foo", Step.PULL, action_type=ActionType.SKIP, reason="already ran")
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    # change the file, and build

    Path("dir1/foo").touch()

    actions = lcm.plan(Step.BUILD)
    assert actions == [
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.UPDATE,
            reason="source changed",
            properties=ActionProperties(changed_files=["foo"], changed_dirs=[]),
        ),
        Action(
            "foo",
            Step.BUILD,
            action_type=ActionType.UPDATE,
            reason="'PULL' step changed",
            project_vars=None,
            properties=ActionProperties(changed_files=["foo"], changed_dirs=[]),
        ),
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    assert capfd.readouterr().out == "Changed files: [foo]\n"


def test_changesets_reload_state(new_dir, mocker, capfd):
    plugins.register({"example": ExamplePlugin})

    Path("dir1").mkdir()
    Path("dir1/foo").touch()

    data = yaml.safe_load(
        textwrap.dedent(
            """\
            parts:
              foo:
                plugin: example
                source: dir1
            """
        )
    )

    lcm = craft_parts.LifecycleManager(
        application_name="example",
        all_parts=data,
        cache_dir=Path(),
    )

    # build parts

    actions = lcm.plan(Step.BUILD)
    assert actions == [
        Action("foo", Step.PULL),
        Action("foo", Step.BUILD),
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    assert capfd.readouterr().out == "no files changed\n"

    # change the file, and pull

    Path("dir1/foo").touch()

    actions = lcm.plan(Step.PULL)
    assert actions == [
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.UPDATE,
            reason="source changed",
            properties=ActionProperties(changed_files=["foo"], changed_dirs=[]),
        )
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    # run build reloading any existing state
    # the state of changed files must be preserved

    actions = lcm.plan(Step.BUILD)
    assert actions == [
        Action(
            "foo",
            Step.PULL,
            action_type=ActionType.SKIP,
            reason="already ran",
        ),
        Action(
            "foo",
            Step.BUILD,
            action_type=ActionType.UPDATE,
            reason="'PULL' step changed",
            project_vars=None,
            properties=ActionProperties(changed_files=["foo"], changed_dirs=[]),
        ),
    ]

    with lcm.action_executor() as aex:
        aex.execute(actions)

    assert capfd.readouterr().out == "Changed files: [foo]\n"
