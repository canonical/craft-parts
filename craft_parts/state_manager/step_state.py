# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2025 Canonical Ltd.
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

"""The step state preserves step execution context information."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from craft_parts.infos import ProjectVar
from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


class MigrationContents(BaseModel):
    """Files and directories migrated."""

    files: set[str] = set()
    directories: set[str] = set()


class MigrationState(BaseModel):
    """State information collected when migrating steps.

    The migration state contains the paths to the files and directories
    that have been migrated. This information is used to remove migrated
    files from shared areas on step cleanup.
    """

    partition: str | None = None
    files: set[str] = set()
    directories: set[str] = set()
    partitions_contents: dict[str, MigrationContents] = Field(default_factory=dict)

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "MigrationState":
        """Create and populate a new state object from dictionary data.

        :param data: A dictionary containing the data to unmarshal.

        :returns: The state object containing the migration data.
        """
        return cls.model_validate(data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the part state data.

        :return: The newly created dictionary.
        """
        return self.model_dump(by_alias=True)

    def write(self, filepath: Path) -> None:
        """Write state data to disk.

        :param filepath: The path to the file to write.
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        yaml_data = yaml.safe_dump(self.model_dump())
        os_utils.TimedWriter.write_text(filepath, yaml_data)

    def contents(self, partition: str | None) -> tuple[set[str], set[str]] | None:
        """Return migrated contents for a given partition."""
        if partition is None or partition == self.partition:
            return self.files, self.directories
        partition_content = self.partitions_contents.get(partition)
        if partition_content:
            return partition_content.files, partition_content.directories

        return None

    def add(
        self, *, files: set[str] | None = None, directories: set[str] | None = None
    ) -> None:
        """Add files and directories to migrated contents."""
        if files:
            self.files |= files
        if directories:
            self.directories |= directories


class StepState(MigrationState, ABC):
    """Contextual information collected when a step is executed.

    The step state contains environmental and project-specific configuration
    data collected at step run time. Those properties are used to decide whether
    the step should run again on a new lifecycle execution.
    """

    part_properties: dict[str, Any] = {}
    project_options: dict[str, Any] = {}
    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        frozen=True,
        alias_generator=lambda s: s.replace("_", "-"),
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def _coerce_project_vars(self) -> Self:
        """Coerce project_vars options to ProjectVar types."""
        # FIXME: add proper type definition for project_options so that
        # ProjectVar can be created by pydantic during model unmarshaling.
        if self.project_options:
            pvars = self.project_options.get("project_vars")
            if pvars:
                for key, val in pvars.items():
                    self.project_options["project_vars"][key] = (
                        ProjectVar.model_validate(val)
                    )

        return self

    @abstractmethod
    def properties_of_interest(
        self,
        part_properties: dict[str, Any],
        *,
        extra_properties: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return relevant properties concerning this step."""

    @abstractmethod
    def project_options_of_interest(
        self, project_options: dict[str, Any]
    ) -> dict[str, Any]:
        """Return relevant project options concerning this step."""

    def diff_properties_of_interest(
        self, other_properties: dict[str, Any], also_compare: list[str] | None = None
    ) -> set[str]:
        """Return properties of interest that differ.

        Take a dictionary of properties and compare to our own, returning
        the set of property names that are different. Both dictionaries
        are filtered prior to comparison, only relevant properties are
        compared.

        :param other_properties: The properties to compare to the
            project options stored in this state.
        """
        return _get_differing_keys(
            self.properties_of_interest(
                self.part_properties, extra_properties=also_compare
            ),
            self.properties_of_interest(
                other_properties, extra_properties=also_compare
            ),
        )

    def diff_project_options_of_interest(
        self, other_project_options: dict[str, Any]
    ) -> set[str]:
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

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "StepState":  # noqa: ARG003
        """Create and populate a new state object from dictionary data."""
        raise RuntimeError("this must be implemented by the step-specific class.")


def _get_differing_keys(dict1: dict[str, Any], dict2: dict[str, Any]) -> set[str]:
    """Return the keys of dictionary entries with different values.

    Given two dictionaries, return a set containing the keys for entries
    that don't have the same value in both dictionaries. Entries with value
    of None are equivalent to a non-existing entry.
    """
    differing_keys = set()
    for key, dict1_value in dict1.items():
        dict2_value = dict2.get(key)
        if dict1_value != dict2_value:
            logger.debug("%s: %r != %r", key, dict1_value, dict2_value)
            differing_keys.add(key)

    for key, dict2_value in dict2.items():
        dict1_value = dict1.get(key)
        if dict1_value != dict2_value:
            logger.debug("%s: %r != %r", key, dict1_value, dict2_value)
            differing_keys.add(key)

    return differing_keys


def validate_hex_string(value: str) -> str:
    """Ensure that a pydantic model field is hexadecimal string."""
    if value:
        bytes.fromhex(value)
    return value
