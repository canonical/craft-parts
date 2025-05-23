# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""Layouts models."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from craft_parts.constraints import SingleEntryDict, UniqueList


class LayoutItem(BaseModel):
    """LayoutItem maps a mountpoint to a craft partition."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        populate_by_name=True,
    )

    mount: str = Field(min_length=1)
    device: str = Field(min_length=1)

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "LayoutItem":
        """Create and populate a new ``LayoutItem`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("layout item data is not a dictionary")

        return LayoutItem(**data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the layout item data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)


Layout = Annotated[UniqueList[LayoutItem], Field(min_length=1)]

Layouts = SingleEntryDict[Literal["default"], Layout]
