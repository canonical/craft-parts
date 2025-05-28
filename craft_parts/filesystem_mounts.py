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

"""FilesystemMounts models."""

from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from craft_parts import errors, features
from craft_parts.constraints import SingleEntryDict, UniqueList


class FilesystemMountItem(BaseModel):
    """FilesystemMountItem maps a mountpoint to a device."""

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
            return self.mount == cast(FilesystemMountItem, other).mount

        return False

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "FilesystemMountItem":
        """Create and populate a new ``FilesystemMountItem`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("filesystem_mount item data is not a dictionary")

        return FilesystemMountItem(**data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the filesystem_mount item data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)


class FilesystemMount(RootModel):
    """FilesystemMount defines the order in which devices should be mounted."""

    root: Annotated[UniqueList[FilesystemMountItem], Field(min_length=1)]

    @field_validator("root", mode="after")
    @classmethod
    def first_maps_to_slash(
        cls, value: list[FilesystemMountItem]
    ) -> list[FilesystemMountItem]:
        """Make sure the first item in the list maps the '/' mount."""
        if value[0].mount != "/":
            raise ValueError("A filesystem first entry must map the '/' mount.")
        return value

    @classmethod
    def unmarshal(cls, data: list[dict[str, Any]]) -> "FilesystemMount":
        """Create and populate a new ``FilesystemMount`` object from list.

        The unmarshal method validates entries in the input list, populating
        the corresponding fields in the data object.

        :param data: The list to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a list.
        """
        if not isinstance(data, list):
            raise TypeError("filesystem_mount data is not a list")

        return FilesystemMount(
            root=[FilesystemMountItem.unmarshal(item) for item in data]
        )

    def marshal(self) -> list[dict[str, Any]]:
        """Create a list containing the filesystem_mount data.

        :return: The newly created list.

        """
        return cast(list[dict[str, Any]], self.model_dump(by_alias=True))


FilesystemMounts = SingleEntryDict[Literal["default"], FilesystemMount]


def validate_filesystem_mount(data: list[dict[str, Any]]) -> None:
    """Validate a filesystem_mount.

    :param data: The filesystem mount data to validate.
    """
    FilesystemMount.unmarshal(data)


def validate_filesystem_mounts(filesystem_mounts: dict[str, Any] | None) -> None:
    """Validate the filesystems section.

    If filesystems are defined then both partition and overlay features must
    be enabled.
    A filesystem_mounts dict must only have a single "default" entry.
    The first entry in default must map the '/' mount.
    """
    if not filesystem_mounts:
        return

    if (
        not features.Features().enable_partitions
        or not features.Features().enable_overlay
    ):
        raise errors.FilesystemMountError(
            brief="Missing features to use filesystems",
            details="Filesystems are defined but partition feature or overlay feature are not enabled.",
        )

    if len(filesystem_mounts) > 1:
        raise errors.FilesystemMountError(
            brief="Exactly one filesystem must be defined.",
            resolution="Define a single entry in the filesystems section of the project file.",
        )

    default_filesystem_mount = filesystem_mounts.get("default")
    if default_filesystem_mount is None:
        raise errors.FilesystemMountError(
            brief="'default' filesystem missing.",
            resolution="Define a 'default' entry in the filesystems section.",
        )

    validate_filesystem_mount(default_filesystem_mount)
