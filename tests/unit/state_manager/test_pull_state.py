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

import pytest
import yaml
from craft_parts.state_manager.pull_state import PullState


class TestPullState:
    """Verify PullState initialization and marshaling."""

    def test_marshal_empty(self):
        state = PullState()
        assert state.marshal() == {
            "assets": {},
            "part-properties": {},
            "project-options": {},
            "files": set(),
            "directories": set(),
            "outdated-files": None,
            "outdated-dirs": None,
        }

    def test_marshal_unmarshal(self):
        state_data = {
            "assets": {"stage-packages": ["foo"]},
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
            "outdated-files": ["a"],
            "outdated-dirs": ["b"],
        }

        state = PullState.unmarshal(state_data)
        assert state.marshal() == state_data

    def test_unmarshal_invalid(self):
        with pytest.raises(TypeError) as raised:
            PullState.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
        assert str(raised.value) == "state data is not a dictionary"


@pytest.mark.usefixtures("new_dir")
class TestPullStatePersist:
    """Verify writing StepState to file."""

    def test_write(self, properties):
        state = PullState(
            assets={"stage-packages": ["foo"]},
            part_properties=properties,
            project_options={
                "target_arch": "amd64",
            },
            files={"a"},
            directories={"b"},
        )

        state.write(Path("state"))
        with open("state") as f:
            content = f.read()

        new_state = yaml.safe_load(content)
        assert PullState.unmarshal(new_state).marshal() == state.marshal()


class TestPullStateChanges:
    """Verify state comparison methods."""

    def test_property_changes(self, properties):
        state = PullState(part_properties=properties)

        relevant_properties = [
            "plugin",
            "source",
            "source-commit",
            "source-depth",
            "source-tag",
            "source-type",
            "source-branch",
            "source-subdir",
            "source-submodules",
            "override-pull",
            "stage-packages",
        ]

        for prop in properties:
            other = properties.copy()
            other[prop] = "new value"

            if prop in relevant_properties:
                # relevant project options changed
                assert state.diff_properties_of_interest(other) == {prop}
            else:
                # relevant properties didn't change
                assert state.diff_properties_of_interest(other) == set()

    def test_project_option_changes(self, project_options):
        state = PullState(project_options=project_options)
        assert state.diff_project_options_of_interest({}) == set()

    def test_extra_property_changes(self, properties):
        augmented_properties = {**properties, "extra-property": "foo"}
        state = PullState(part_properties=augmented_properties)

        relevant_properties = [
            "plugin",
            "source",
            "source-commit",
            "source-depth",
            "source-tag",
            "source-type",
            "source-branch",
            "source-subdir",
            "source-submodules",
            "override-pull",
            "stage-packages",
            "extra-property",
        ]

        for prop in augmented_properties:
            other = augmented_properties.copy()
            other[prop] = "new value"

            diff = state.diff_properties_of_interest(
                other, also_compare=["extra-property"]
            )
            if prop in relevant_properties:
                # relevant project options changed
                assert diff == {prop}
            else:
                # relevant properties didn't change
                assert diff == set()
