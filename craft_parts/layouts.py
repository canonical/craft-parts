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

from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from craft_parts.constraints import SingleEntryDict, UniqueList


class LayoutItem(BaseModel):
    """LayoutItem maps a mountpoint to a device."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        populate_by_name=True,
    )

    mount: str = Field(min_length=1)
    device: str = Field(min_length=1)

    def __hash__(self) -> int:
        return str.__hash__(self.mount)

    def __eq__(self, other: object) -> bool:
        if type(other) is type(self):
            return self.mount == cast(LayoutItem, other).mount

        return False

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


class Layout(RootModel):
    """Layout defines the order in which devices should be mounted."""

    root: Annotated[UniqueList[LayoutItem], Field(min_length=1)]

    @field_validator("root", mode="after")
    @classmethod
    def first_maps_to_slash(cls, value: list[LayoutItem]) -> list[LayoutItem]:
        """Make sure the first item in the list maps the '/' mount."""
        if value[0].mount != "/":
            raise ValueError("A filesystem first entry must map the '/' mount.")
        return value

    @classmethod
    def unmarshal(cls, data: list[dict[str, Any]]) -> "Layout":
        """Create and populate a new ``Layout`` object from list.

        The unmarshal method validates entries in the input list, populating
        the corresponding fields in the data object.

        :param data: The list to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a list.
        """
        if not isinstance(data, list):
            raise TypeError("layout data is not a list")

        return Layout(root=[LayoutItem.unmarshal(item) for item in data])

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the layout item data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)


Layouts = SingleEntryDict[Literal["default"], Layout]
