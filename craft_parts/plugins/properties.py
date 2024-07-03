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

from typing import Any

from pydantic import ConfigDict, BaseModel


class PluginPropertiesModel(BaseModel):
    """Model for plugins properties using pydantic validation."""
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        frozen=True,
        alias_generator=lambda s: s.replace("_", "-")
    )


class PluginProperties(PluginPropertiesModel):
    """Options specific to a plugin.

    PluginProperties should be subclassed into plugin-specific property
    classes and populated from a dictionary containing part properties.

    By default all plugin properties will be compared to check if the
    build step is dirty. This can be overridden in each plugin if needed.
    """

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "PluginProperties":  # noqa: ARG003
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.
        """
        return cls()

    def marshal(self) -> dict[str, Any]:
        """Obtain a dictionary containing the plugin properties."""
        return self.dict(by_alias=True)

    @classmethod
    def get_pull_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the pull stage."""
        return []

    @classmethod
    def get_build_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the build stage."""
        properties = cls.schema(by_alias=True).get("properties")
        return list(properties.keys()) if properties else []
