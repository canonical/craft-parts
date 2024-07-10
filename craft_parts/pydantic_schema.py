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

import pathlib
import re
from typing import Annotated, Any, cast

from overrides import override
import pydantic
import pydantic_core

from craft_parts import plugins, sources
from craft_parts.plugins import plugins as int_plugins
from craft_parts.plugins.dump_plugin import DumpPlugin
from craft_parts.plugins.nil_plugin import NilPlugin, NilPluginProperties
from craft_parts.plugins.rust_plugin import RustPlugin


class Part(pydantic.BaseModel):
    """Generic schema for all parts."""

    plugin_data: plugins.PluginProperties
    source_data: sources.PartSourceModel

    def __init__(self, /, **data: Any) -> None:
        if "plugin" not in data:
            raise ValueError("a part requires a 'plugin' key")
        plugin_class = plugins.get_plugin_class(data["plugin"])
        plugin_data = plugin_class.properties_class.unmarshal(data)
        source_adapter = pydantic.TypeAdapter(sources.PartSourceModel)
        source_raw_data = {key: val for key, val in data.items() if key.startswith("source")}
        source_data = source_adapter.validate_python(source_raw_data)

        super().__init__(plugin_data=plugin_data, source_data=source_data)


    @classmethod
    @override
    def model_json_schema(cls, by_alias: bool = True, ref_template: str = pydantic.json_schema.DEFAULT_REF_TEMPLATE, schema_generator: type[pydantic.json_schema.GenerateJsonSchema] = pydantic.json_schema.GenerateJsonSchema, mode: pydantic.json_schema.JsonSchemaMode = 'validation') -> dict[str, Any]:
        registered_plugins = plugins.get_registered_plugins()
        plugin_models = [plugin.properties_class for plugin in registered_plugins.values()]
        plugin_union = plugin_models[0]
        for model in plugin_models[1:]:
            plugin_union |= model

        PluginModel = Annotated[plugin_union, pydantic.Discriminator("plugin"), pydantic.ConfigDict(extra="allow")]

        source_adapter = pydantic.TypeAdapter(sources.PartSourceModel)
        plugin_adapter = pydantic.TypeAdapter(PluginModel)
        source_json_schema = source_adapter.json_schema(by_alias=by_alias, ref_template=ref_template, schema_generator=schema_generator, mode=mode)
        plugin_json_schema = plugin_adapter.json_schema(by_alias=by_alias, ref_template=ref_template, schema_generator=schema_generator, mode=mode)

        source_defs = source_json_schema.pop("$defs")
        for model in source_defs.values():
            # Allow properties not prefixed with "source" in source models
            model["patternProperties"] = {r"^(?!source-)": {}}
        plugin_defs = plugin_json_schema.pop("$defs")
        for model in plugin_defs.values():
            # Allow "source-" prefixed properties in plugin models
            model["patternProperties"] = {r"^source\-": {}}

        return {
            "$defs": source_defs | plugin_defs,
            "allOf": [
                plugin_json_schema,
                source_json_schema,
            ]
        }
