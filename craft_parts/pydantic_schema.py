# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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
"""Experiments with pydantic schemas."""

from functools import reduce
from typing import Annotated, Any, TypeAlias, cast

import pydantic
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaMode,
)
from typing_extensions import override

from craft_parts import plugins, sources
from craft_parts.plugins.nil_plugin import NilPluginProperties


class Part(pydantic.BaseModel):
    """Generic schema for all parts."""

    plugin_data: plugins.PluginProperties
    source_data: sources.SourceModel

    def __init__(self, /, **data: Any) -> None:
        if "plugin" not in data:
            raise ValueError("a part requires a 'plugin' key")
        plugin_class = plugins.get_plugin_class(data["plugin"])
        plugin_data = plugin_class.properties_class.unmarshal(data)
        source_raw_data = {
            key: val for key, val in data.items() if key.startswith("source")
        }
        source_data: sources.SourceModel = pydantic.TypeAdapter(  # type: ignore[reportUnknownVariableType]
            sources.SourceModel
        ).validate_python(source_raw_data)

        super().__init__(plugin_data=plugin_data, source_data=source_data)

    @classmethod
    @override
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = "validation",
    ) -> dict[str, Any]:
        """Create the JSON schema for a Part."""
        registered_plugins = plugins.get_registered_plugins()
        plugin_models = [
            cast(TypeAlias, plugin.properties_class)
            for plugin in registered_plugins.values()
        ]

        # This type is not actually used outside of schema generation, so it is acceptable
        # to be dynamically defined at runtime
        PluginUnion: TypeAlias = reduce(lambda acc, ty: acc | ty, plugin_models)  # type: ignore[reportInvalidTypeForm, valid-type]

        plugin_model = Annotated[
            PluginUnion,
            pydantic.Discriminator("plugin"),
            pydantic.ConfigDict(extra="allow"),
        ]

        source_adapter = pydantic.TypeAdapter(sources.SourceModel)  # type: ignore[reportUnknownVariableType, var-annotated]
        plugin_adapter = pydantic.TypeAdapter(plugin_model)  # type: ignore[reportUnknownVariableType]
        source_json_schema = source_adapter.json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
        )
        plugin_json_schema = plugin_adapter.json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
        )

        source_defs = source_json_schema.pop("$defs")
        for model in source_defs.values():
            # Allow properties not prefixed with "source" in source models
            model["patternProperties"] = {r"^(?!source-)": {}}  # type:ignore[index]
        plugin_defs = plugin_json_schema.pop("$defs")
        for model in plugin_defs.values():
            # Allow extra parts properties for the plugin.
            model["patternProperties"] = {  # type:ignore[index]
                r"^source\-": {},
                r"^override\-": {"type": "string"},
                r"^(build|stage)\-(packages|snaps)$": {"type": "array"},
            }

        return {
            "$defs": source_defs | plugin_defs,
            "anyOf": [
                {"allOf": [plugin_json_schema, source_json_schema]},
                NilPluginProperties.model_json_schema(),
            ],
        }


class PartsFile(pydantic.BaseModel):
    """A root model for a file that contains a 'parts' key."""

    parts: dict[str, Any]

    @classmethod
    @override
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = "validation",
    ) -> dict[str, Any]:
        """Create the JSON schema for a file with Parts."""
        schema = super().model_json_schema(
            by_alias, ref_template, schema_generator, mode
        )
        part_schema = Part.model_json_schema()
        schema.setdefault("$defs", {}).update(part_schema.pop("$defs"))
        schema["properties"]["parts"]["additionalProperties"] = part_schema
        return schema
