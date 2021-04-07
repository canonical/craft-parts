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

from pathlib import Path
from typing import Any, Dict

import yaml

from craft_parts.state_manager.step_state import StepState


class SomeStepState(StepState):
    """A concrete step state implementing abstract methods."""

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": part_properties.get("name")}

    def project_options_of_interest(
        self, part_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"number": part_properties.get("number")}


class TestStepState:
    """Verify StepState initialization and marshaling."""

    def test_marshal_empty(self):
        state = SomeStepState()
        assert state.marshal() == {
            "properties": {},
            "project-options": {},
            "files": set(),
            "directories": set(),
        }

    def test_marshal_data(self):
        state = SomeStepState(
            part_properties={
                "name": "foo",
            },
            project_options={
                "number": 42,
            },
            files={"a"},
            directories={"b"},
        )
        assert state.marshal() == {
            "properties": {"name": "foo"},
            "project-options": {"number": 42},
            "files": {"a"},
            "directories": {"b"},
        }

    def test_ignore_additional_data(self):
        state = SomeStepState(extra="something")
        assert state.marshal() == {
            "properties": {},
            "project-options": {},
            "files": set(),
            "directories": set(),
        }


class TestStepStatePersist:
    """Verify writing StepState to file."""

    def test_write(self, new_dir):
        state = SomeStepState(
            part_properties={
                "name": "foo",
            },
            project_options={
                "number": 42,
            },
            files={"a"},
            directories={"b"},
        )

        state.write(Path("state"))
        with open("state") as f:
            content = f.read()

        new_state = yaml.safe_load(content)
        assert new_state == state.marshal()


class TestStateChanges:
    """Verify state comparison methods."""

    def test_property_changes(self):
        state = SomeStepState(
            part_properties={
                "name": "alice",
                "pet": "spider",
            },
        )

        # relevant properties didn't change
        assert (
            state.diff_properties_of_interest({"name": "alice", "pet": "eel"}) == set()
        )

        # relevant properties changed
        assert state.diff_properties_of_interest({"name": "bob"}) == {"name"}

    def test_project_options_changes(self):
        state = SomeStepState(
            project_options={
                "number": 42,
                "useful": False,
            },
        )

        # relevant project options didn't change
        assert (
            state.diff_project_options_of_interest({"number": 42, "useful": True})
            == set()
        )

        # relevant project options changed
        assert state.diff_project_options_of_interest({"number": 50}) == {"number"}
