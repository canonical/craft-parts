# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""The step state preserves step execution context information."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Hashable, Set

from pydantic_yaml import YamlModel  # type: ignore


class StepState(YamlModel, ABC):
    """Contextual information collected when a step is executed.

    The step state contains environmental and project-specific configuration
    data collected at step run time. Those properties are used to decide whether
    the step should run again on a new lifecycle execution.
    """

    part_properties: Dict[str, Any] = {}
    project_options: Dict[str, Any] = {}
    files: Set[str] = set()
    directories: Set[str] = set()

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "ignore"
        allow_mutation = False
        alias_generator = lambda s: s.replace("_", "-")  # noqa: E731
        allow_population_by_field_name = True

    @abstractmethod
    def properties_of_interest(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return relevant properties concerning this step."""

    @abstractmethod
    def project_options_of_interest(
        self, project_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return relevant project options concerning this step."""

    def diff_properties_of_interest(self, other_properties: Dict[str, Any]) -> Set[str]:
        """Return properties of interest that differ.

        Take a dictionary of properties and compare to our own, returning
        the set of property names that are different. Both dictionaries
        are filtered prior to comparison, only relevant properties are
        compared.

        :param other_properties: The properties to compare to the
            project options stored in this state.
        """
        return _get_differing_keys(
            self.properties_of_interest(self.part_properties),
            self.properties_of_interest(other_properties),
        )

    def diff_project_options_of_interest(
        self, other_project_options: Dict[str, Any]
    ) -> Set[str]:
        """Return project options that differ.

        Take a dictionary of project_options and compare to our own,
        returning the set of project option names that are different. Both
        dictionaries are filtered prior to comparison, only relevant
        options are compared.

        :param other_project_options: The project options to compare to
           the project options stored in this state.
        """
        return _get_differing_keys(
            self.project_options_of_interest(self.project_options),
            self.project_options_of_interest(other_project_options),
        )

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the part state data.

        :return: The newly created dictionary.
        """
        return self.dict(by_alias=True)

    def write(self, filepath: Path) -> None:
        """Write this state to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        yaml_data = self.yaml(by_alias=True)
        filepath.write_text(yaml_data)


def _get_differing_keys(
    dict1: Dict[str, Hashable], dict2: Dict[str, Hashable]
) -> Set[str]:
    """Return the keys of dictionary entries with different values.

    Given two dictionaries, return a set containing the keys for entries
    that don't have the same value in both dictionaries. Entries with value
    of None are equivalent to a non-existing entry.
    """
    # TODO: refactor implementation
    #       can we use something similar to what @cjp256 suggested in
    #       https://github.com/canonical/craft-parts/pull/10/?
    differing_keys = set()
    for key, dict1_value in dict1.items():
        dict2_value = dict2.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    for key, dict2_value in dict2.items():
        dict1_value = dict1.get(key)
        if dict1_value != dict2_value:
            differing_keys.add(key)

    return differing_keys
