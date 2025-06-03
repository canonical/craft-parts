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

from collections.abc import Iterable, Iterator
from typing import Annotated, Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
    field_validator,
)

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

    @field_validator("device", mode="after")
    @classmethod
    def strip_parenthesis(cls, value: str) -> str:
        """Strip parenthesis until a better integration with partitions."""
        return value.strip("()")

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
            raise TypeError("Filesystem input data must be a dictionary.")

        return cls.model_validate(data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the filesystem_mount item data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)


class FilesystemMount(RootModel):
    """FilesystemMount defines the order in which devices should be mounted."""

    root: Annotated[UniqueList[FilesystemMountItem], Field(min_length=1)]

    def __iter__(self) -> Iterator[FilesystemMountItem]:  # type: ignore[override]
        return iter(self.root)

    def __reversed__(self) -> Iterator[FilesystemMountItem]:
        return reversed(self.root)

    @field_validator("root", mode="after")
    @classmethod
    def first_maps_to_slash(
        cls, value: list[FilesystemMountItem]
    ) -> list[FilesystemMountItem]:
        """Make sure the first item in the list maps the '/' mount."""
        if value[0].mount != "/":
            raise ValueError("The first entry in a filesystem must map the '/' mount.")
        return value

    @classmethod
    def unmarshal(cls, data: list[dict[str, Any]]) -> "FilesystemMount":
        """Create and populate a new ``FilesystemMount`` object from list.

        The unmarshal method validates entries in the input list, populating
        the corresponding fields in the data object.

        :param data: The list to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a list.
        :raise pydantic.ValidationError: If the data fails validation.
        """
        if not isinstance(data, list):
            raise TypeError("Filesystem entry must be a list.")

        return cls.model_validate(
            [FilesystemMountItem.unmarshal(item) for item in data]
        )

    def marshal(self) -> list[dict[str, Any]]:
        """Create a list containing the filesystem_mount data.

        :return: The newly created list.

        """
        return cast(list[dict[str, Any]], self.model_dump(by_alias=True))


class FilesystemMounts(RootModel):
    """FilesystemMounts defines list of FilesystemMount."""

    root: SingleEntryDict[Literal["default"], FilesystemMount]

    def __iter__(self) -> Iterator[Literal["default"]]:  # type: ignore[override]
        return iter(self.root)

    def __getitem__(self, item: Literal["default"]) -> FilesystemMount | None:
        return self.root.get(item)

    def get(
        self, key: Literal["default"], default: FilesystemMount | None = None
    ) -> FilesystemMount | None:
        """Return a specific item of the underlying dict."""
        return self.root.get(key, default)

    def items(self) -> Iterable[tuple[Literal["default"], FilesystemMount]]:
        """Return items of the underlying dict."""
        return self.root.items()

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "FilesystemMounts":
        """Create and populate a new ``FilesystemMounts`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("filesystems is not a dictionary")

        return cls.model_validate(data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the filesystem_mounts data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)  # type: ignore[no-any-return]


def validate_filesystem_mount(data: list[dict[str, Any]]) -> None:
    """Validate a filesystem_mount.

    :param data: The filesystem mount data to validate.

    :raises: ValueError if the filesystem mount is not valid.
    """
    FilesystemMount.unmarshal(data)


def validate_filesystem_mounts(filesystem_mounts: dict[str, Any] | None) -> None:
    """Validate the filesystems section.

    If filesystems are defined then both partition and overlay features must
    be enabled.
    A filesystem_mounts dict must only have a single "default" entry.
    The first entry in default must map the '/' mount.

    :raises: FilesystemMountError if the filesystem mounts are not valid.
    """
    if not filesystem_mounts:
        return

    if (
        not features.Features().enable_partitions
        or not features.Features().enable_overlay
    ):
        raise errors.FilesystemMountError(
            brief="Missing features to use filesystems",
            resolution="Enable both the partition and overlay features.",
        )

    if len(filesystem_mounts) > 1:
        raise errors.FilesystemMountError(
            brief="Only one filesystem can be defined.",
            resolution="Reduce the filesystems section to a single entry.",
        )

    default_filesystem_mount = filesystem_mounts.get("default")
    if default_filesystem_mount is None:
        raise errors.FilesystemMountError(
            brief="'default' filesystem missing.",
            resolution="Define a 'default' entry in the filesystems section.",
        )

    try:
        validate_filesystem_mount(default_filesystem_mount)
    except ValidationError as err:
        raise errors.FilesystemMountError.from_validation_error(
            error_list=err.errors(),
        ) from err
    except TypeError as err:
        raise errors.FilesystemMountError(
            brief="Filesystem validation failed.",
            details=str(err),
        ) from err
