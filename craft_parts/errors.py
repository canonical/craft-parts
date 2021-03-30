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

"""Craft parts errors."""

import dataclasses
from pathlib import Path
from typing import List, Optional, Union

import jsonschema  # type: ignore

from craft_parts.utils import schema_helpers


@dataclasses.dataclass(repr=True)
class PartsError(Exception):
    """Unexpected error.

    :param brief: Brief description of error.
    :param details: Detailed information.
    :param resolution: Recommendation, if any.
    """

    brief: str
    details: Optional[str] = None
    resolution: Optional[str] = None

    def __str__(self) -> str:
        components = [self.brief]

        if self.details:
            components.append(self.details)

        if self.resolution:
            components.append(self.resolution)

        return "\n".join(components)


class PartDependencyCycle(PartsError):
    """A dependency cycle has been detected in the parts definition."""

    def __init__(self) -> None:
        brief = "A circular dependency chain was detected."
        resolution = "Review the parts definition to remove dependency cycles."

        super().__init__(brief=brief, resolution=resolution)


class InvalidPartName(PartsError):
    """An operation was requested on a part that's in the parts specification.

    :param part_name: The invalid part name.
    """

    def __init__(self, part_name: str):
        self.part_name = part_name
        brief = f"A part named {part_name!r} is not defined in the parts list."
        resolution = "Review the parts definition and make sure it's correct."

        super().__init__(brief=brief, resolution=resolution)


class InvalidArchitecture(PartsError):
    """The machine architecture is not supported.

    :param arch_name: The unsupported architecture name.
    """

    def __init__(self, arch_name: str):
        self.arch_name = arch_name
        brief = f"Architecture {arch_name!r} is not supported."
        resolution = "Make sure the architecture name is correct."

        super().__init__(brief=brief, resolution=resolution)


class SchemaNotFound(PartsError):
    """Failed to find the schema definition file.

    :param path: The path to the schema file.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = str(path)
        brief = f"Unable to find the schema definition file {self.path!r}."
        resolution = "Make sure craft-parts is correctly installed."

        super().__init__(brief=brief, resolution=resolution)


class SchemaValidationError(PartsError):
    """The parts data failed schema validation.

    :param message: the error message from the schema validator.
    """

    def __init__(self, message: str):
        brief = "Schema validation error."
        details = message
        resolution = "Review the YAML file and make sure it conforms to the schema."

        super().__init__(brief=brief, details=details, resolution=resolution)

    @classmethod
    def from_validation_error(cls, error: jsonschema.ValidationError):
        """Reformat a jsonschema.ValidationError to make it a bit more understandable."""
        messages: List[str] = []

        preamble = schema_helpers.determine_preamble(error)
        cause = schema_helpers.determine_cause(error)
        supplement = schema_helpers.determine_supplemental_info(error)

        if preamble:
            messages.append(preamble)

        # If we have a preamble we are not at the root
        if supplement and preamble:
            messages.append(error.message)
            messages.append(f"({supplement})")
        elif supplement:
            messages.append(supplement)
        elif cause:
            messages.append(cause)
        else:
            messages.append(error.message)

        return cls(" ".join(messages))
