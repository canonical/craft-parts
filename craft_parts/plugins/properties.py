# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

"""Definitions and helpers for plugin options."""

from typing import Any, ClassVar, Collection

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self


def extract_plugin_properties(
    data: dict[str, Any], *, plugin_name: str, required: Collection[str] | None = None
) -> dict[str, Any]:
    """Obtain plugin-specifc entries from part properties.

    Plugin-specifc properties must be prefixed with the name of the plugin.

    :param data: A dictionary containing all part properties.
    :plugin_name: The name of the plugin.

    :return: A dictionary with plugin properties.
    """
    if required is None:
        required = []

    plugin_data: dict[str, Any] = {}
    prefix = f"{plugin_name}-"

    for key, value in data.items():
        if key.startswith(prefix) or key in required:
            plugin_data[key] = value

    return plugin_data


class PluginProperties(BaseModel, frozen=True):
    """Options specific to a plugin.

    PluginProperties should be subclassed into plugin-specific property
    classes and populated from a dictionary containing part properties.

    By default all plugin properties will be compared to check if the
    build step is dirty. This can be overridden in each plugin if needed.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        frozen=True,
        alias_generator=lambda s: s.replace("_", "-"),
    )
    plugin: str = ""

    _required_fields: ClassVar[Collection[str]] = ("source",)

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> Self:
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.
        :param required: A collection of required property names that don't begin with
            the plugin prefix.
        :return: The populated plugin properties data object.
        """
        return cls.model_validate(
            extract_plugin_properties(
                data, plugin_name=cls.__fields__["plugin"].default,
                required=cls._required_fields,
            )
        )

    def marshal(self) -> dict[str, Any]:
        """Obtain a dictionary containing the plugin properties."""
        return self.dict(by_alias=True, exclude={"plugin"})

    @classmethod
    def get_pull_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the pull stage."""
        return []

    @classmethod
    def get_build_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the build stage."""
        properties = cls.schema(by_alias=True).get("properties")
        if properties:
            del properties["plugin"]
            return list(properties.keys())
        return []
