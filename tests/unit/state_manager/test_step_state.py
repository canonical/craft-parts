# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

from pathlib import Path
from typing import Any

import pytest
import yaml
from craft_parts.state_manager import step_state


class TestMigrationState:
    """Verify MigrationState handling."""

    def test_marshal_empty(self):
        state = step_state.MigrationState()
        assert state.marshal() == {
            "files": set(),
            "directories": set(),
        }

    def test_marshal_data(self):
        state = step_state.MigrationState(
            files={"a", "b", "c"},
            directories={"d", "e", "f"},
        )
        assert state.marshal() == {
            "files": {"a", "b", "c"},
            "directories": {"d", "e", "f"},
        }

    def test_unmarshal(self):
        data = {
            "files": {"a", "b", "c"},
            "directories": {"d", "e", "f"},
        }
        state = step_state.MigrationState.unmarshal(data)
        assert state.marshal() == data


class SomeStepState(step_state.StepState):
    """A concrete step state implementing abstract methods."""

    def properties_of_interest(
        self,
        part_properties: dict[str, Any],
        *,
        extra_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        return {"name": part_properties.get("name")}

    def project_options_of_interest(
        self, project_options: dict[str, Any]
    ) -> dict[str, Any]:
        return {"number": project_options.get("number")}


class TestStepState:
    """Verify StepState initialization and marshaling."""

    def test_marshal_empty(self):
        state = SomeStepState()
        assert state.marshal() == {
            "part-properties": {},
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
            "part-properties": {"name": "foo"},
            "project-options": {"number": 42},
            "files": {"a"},
            "directories": {"b"},
        }

    def test_ignore_additional_data(self):
        state = SomeStepState(extra="something")  # type: ignore[reportGeneralTypeIssues]
        assert state.marshal() == {
            "part-properties": {},
            "project-options": {},
            "files": set(),
            "directories": set(),
        }


@pytest.mark.usefixtures("new_dir")
class TestStepStatePersist:
    """Verify writing StepState to file."""

    def test_write(self):
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
        assert SomeStepState.model_validate(new_state) == state


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


class TestHelpers:
    """Tests for helper functions."""

    @pytest.mark.parametrize(
        ("d1", "d2", "result"),
        [
            ({}, {}, set()),
            ({"a": 1}, {}, {"a"}),
            ({}, {"b": 2}, {"b"}),
            ({"a": 1}, {"b": 2}, {"a", "b"}),
            ({"a": None}, {}, set()),
            ({}, {"b": None}, set()),
            ({"a": None}, {"b": None}, set()),
            ({"a": 1}, {"a": 1}, set()),
            ({"a": 1}, {"a": 2}, {"a"}),
            ({"a": None}, {"a": 1}, {"a"}),
            ({"a": 1}, {"a": 1, "b": 2}, {"b"}),
            ({"a": 1, "b": 2}, {"a": 1}, {"b"}),
        ],
    )
    def test_get_differing_keys(self, d1, d2, result):
        assert step_state._get_differing_keys(d1, d2) == result
