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

from craft_parts.state_manager.overlay_state import OverlayState


class TestOverlayStateChanges:
    """Verify overlay state comparison methods."""

    def test_property_changes(self):
        properties = {
            "overlay-script": None,
            "overlay": None,
            "override-overlay": "echo original",
            "override-build": "echo build",
        }
        state = OverlayState(part_properties=properties)

        relevant_properties = [
            "overlay-script",
            "overlay",
            "override-overlay",
        ]

        for prop in properties:
            other = properties.copy()
            other[prop] = "new value"

            if prop in relevant_properties:
                assert state.diff_properties_of_interest(other) == {prop}
            else:
                assert state.diff_properties_of_interest(other) == set()

    def test_extra_property_changes(self):
        properties = {
            "overlay-script": None,
            "overlay": None,
            "override-overlay": "echo original",
            "extra-property": "foo",
        }
        state = OverlayState(part_properties=properties)

        for prop in properties:
            other = properties.copy()
            other[prop] = "new value"

            diff = state.diff_properties_of_interest(
                other, also_compare=["extra-property"]
            )

            assert diff == {prop}
