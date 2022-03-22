# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""State definitions for the pull step."""

from typing import Any, Dict

from .step_state import StepState


class PullState(StepState):
    """Context information for the pull step."""

    assets: Dict[str, Any] = {}

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "PullState":
        """Create and populate a new ``PullState`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the state object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("state data is not a dictionary")

        return cls(**data)

    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return relevant properties concerning this step.

        :param part_properties: A dictionary containing all part properties.

        :return: A dictionary containing properties of interest.
        """
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
            "overlay-packages",
        ]

        properties: Dict[str, Any] = {}
        for name in relevant_properties:
            properties[name] = part_properties.get(name)

        return properties

    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return relevant project options concerning this step.

        :param project_options: A dictionary containing all project options.

        :return: A dictionary containing project options of interest.
        """
        return {
            "project_vars_part_name": project_options.get("project_vars_part_name"),
        }
