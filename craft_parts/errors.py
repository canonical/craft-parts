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
from typing import Any, Dict, List, Optional


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


class PartSpecificationError(PartsError):
    """A part was not correctly specified.

    :param part_name: The part name.
    :param message: The error message.
    """

    def __init__(self, *, part_name: str, message: str):
        self.part_name = part_name
        self.message = message
        brief = f"Part {part_name!r} validation failed."
        details = message
        resolution = f"Review part {part_name!r} and make sure it's correct."

        super().__init__(brief=brief, details=details, resolution=resolution)

    @classmethod
    def from_validation_error(cls, *, part_name: str, error_list: List[Dict[str, Any]]):
        """Create a PartSpecificationError from a pydantic error list."""
        formatted_errors: List[str] = []

        for error in error_list:
            loc = error.get("loc")
            msg = error.get("msg")

            if not (loc and msg) or not isinstance(loc, tuple):
                continue

            fields = ",".join([repr(entry) for entry in loc])
            formatted_errors.append(f"{fields}: {msg}")

        return cls(part_name=part_name, message="\n".join(formatted_errors))


class CopyTreeError(PartsError):
    """Failed to copy or link a file tree.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to copy or link file tree: {message}."
        resolution = "Make sure paths and permissions are correct."

        super().__init__(brief=brief, resolution=resolution)


class CopyFileNotFound(PartsError):
    """An attempt was made to copy a file that doesn't exist.

    :param name: The file name.
    """

    def __init__(self, name: str):
        self.name = name
        brief = f"Failed to copy {name!r}: no such file or directory."

        super().__init__(brief=brief)
