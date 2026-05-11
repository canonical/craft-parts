# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

import pytest
from craft_parts.infos import ProjectOptions
from craft_parts.state_manager.overlay_state import OverlayState


class TestOverlayState:
    """Verify OverlayState initialization and marshaling."""

    def test_marshal_empty(self):
        state = OverlayState()
        assert state.marshal() == {
            "partition": None,
            "part-properties": {},
            "project-options": ProjectOptions().model_dump(),
            "files": set(),
            "directories": set(),
            "partitions-contents": {},
        }

    def test_unmarshal_invalid(self):
        with pytest.raises(TypeError, match="^state data is not a dictionary$"):
            OverlayState.unmarshal(None)  # type: ignore[reportGeneralTypeIssues]


class TestOverlayStateChanges:
    """Verify state comparison methods."""

    def test_property_changes(self, properties):
        state = OverlayState(part_properties=properties)

        relevant_properties = [
            "overlay",
            "overlay-script",
            "override-overlay",
        ]

        for prop in properties:
            other = properties.copy()
            other[prop] = "new value"

            if prop in relevant_properties:
                assert state.diff_properties_of_interest(other) == {prop}
            else:
                assert state.diff_properties_of_interest(other) == set()

    def test_project_option_changes(self, project_options):
        state = OverlayState(project_options=project_options)
        assert state.diff_project_options_of_interest(ProjectOptions()) == set()

    def test_extra_property_changes(self, properties):
        augmented_properties = {**properties, "extra-property": "foo"}
        state = OverlayState(part_properties=augmented_properties)

        relevant_properties = [
            "overlay",
            "overlay-script",
            "override-overlay",
            "extra-property",
        ]

        for prop in augmented_properties:
            other = augmented_properties.copy()
            other[prop] = "new value"

            diff = state.diff_properties_of_interest(
                other, also_compare=["extra-property"]
            )
            if prop in relevant_properties:
                assert diff == {prop}
            else:
                assert diff == set()
