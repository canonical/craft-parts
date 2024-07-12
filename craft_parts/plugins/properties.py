# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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

from collections.abc import Collection
from typing import Any, ClassVar

import pydantic
from typing_extensions import Self

from . import base


# We set `frozen=True` here so that pyright knows to treat variable types as covariant
# rather than invariant, improving the readability of child classes.
# As a side effect, we have to tell mypy not to warn about setting this config item
# twice.
class PluginProperties(pydantic.BaseModel, frozen=True):  # type: ignore[misc]
    """Options specific to a plugin.

    PluginProperties should be subclassed into plugin-specific property
    classes and populated from a dictionary containing part properties.

    By default all plugin properties will be compared to check if the
    build step is dirty. This can be overridden in each plugin if needed.
    """

    model_config = pydantic.ConfigDict(
        alias_generator=lambda s: s.replace("_", "-"),
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )

    plugin: str = ""
    source: str | None = None

    _required_fields: ClassVar[Collection[str]] = ("plugin", "source")

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> Self:
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.
        """
        plugin_name = cls.model_json_schema()["properties"]["plugin"].get("default", "")
        return cls.model_validate(
            base.extract_plugin_properties(
                data,
                plugin_name=plugin_name,
                required=cls._required_fields,
            )
        )

    def marshal(self) -> dict[str, Any]:
        """Obtain a dictionary containing the plugin properties."""
        return self.model_dump(mode="json", by_alias=True, exclude={"plugin"})

    @classmethod
    def get_pull_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the pull stage."""
        return []

    @classmethod
    def get_build_properties(cls) -> list[str]:
        """Obtain the list of properties affecting the build stage."""
        properties = cls.schema(by_alias=True).get("properties", [])
        return [p for p in properties if p != "plugin"]
