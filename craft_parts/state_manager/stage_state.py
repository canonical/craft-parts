# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2023 Canonical Ltd.
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

"""State definitions for the stage step."""

from typing import Any, Dict, List, Optional

from overrides import override
from pydantic import validator

from .step_state import StepState, validate_hex_string


class StageState(StepState):
    """Context information for the stage step."""

    overlay_hash: Optional[str] = None

    _validate_hex_string = validator("overlay_hash", allow_reuse=True)(
        validate_hex_string
    )

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "StageState":
        """Create and populate a new ``StageState`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the state object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("state data is not a dictionary")

        return cls(**data)

    @override
    def properties_of_interest(
        self,
        part_properties: Dict[str, Any],
        *,
        extra_properties: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return relevant properties concerning this step.

        :param part_properties: A dictionary containing all part properties.
        :param extra_properties: Additional relevant properties to be returned.

        :return: A dictionary containing properties of interest.
        """
        relevant_properties = [
            "override-stage",
            "stage",
            *(extra_properties or []),
        ]
        return {name: part_properties.get(name) for name in relevant_properties}

    @override
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
