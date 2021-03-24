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

"""The exceptions that can be raised when using craft_parts."""

from abc import ABC


class CraftPartsError(Exception, ABC):
    """Base class for Craft Parts exceptions."""

    fmt = "Daughter classes should redefine this"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.fmt.format([], **self.__dict__)


class CraftPartsReportableError(CraftPartsError):
    """Base class for reportable Craft Parts exceptions."""


class PartDependencyCycle(CraftPartsError):
    """Dependency cycles have been detected in the parts definition."""

    fmt = (
        "A circular dependency chain was detected. Please review the parts "
        "definition to remove dependency cycles."
    )


class InvalidPartName(CraftPartsError):
    """An operation was requested on a part that's in the parts specification.

    :param part_name: the invalid part name.
    """

    fmt = "A part named {part_name!r} is not defined in the parts list."

    def __init__(self, part_name: str):
        super().__init__(part_name=part_name)
