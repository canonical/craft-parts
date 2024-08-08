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

import functools
from typing import Any, cast

import pydantic
from typing_extensions import Self


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

    @classmethod
    @functools.lru_cache(maxsize=1)
    def model_properties(cls) -> dict[str, dict[str, Any]]:
        """Get the properties for this model from the JSON schema."""
        return cast(
            dict[str, dict[str, Any]], cls.model_json_schema().get("properties", {})
        )

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> Self:
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.
        """
        properties = cls.model_properties()
        plugin_name = properties["plugin"].get("default", "")

        plugin_data = {
            key: value
            for key, value in data.items()
            # Note: We also use startswith here in order to have the Properties object
            # provide an "extra inputs are not permitted" error message.
            if key in properties or key.startswith(f"{plugin_name}-")
        }

        return cls.model_validate(plugin_data)

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
        return [p for p in cls.model_properties() if p != "plugin"]
