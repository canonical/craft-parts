# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Schema validation helpers and definitions."""

import copy
import json
from pathlib import Path
from typing import Any, Dict, Union

import jsonschema  # type: ignore

from craft_parts import errors


class Validator:
    """Parts schema validator.

    :param filename: The schema file name.
    """

    def __init__(self, filename: Union[str, Path]):
        self._load_schema(filename)

    @property
    def schema(self) -> Dict[str, Any]:
        """Return all schema properties."""
        return self._schema["properties"].copy()

    @property
    def part_schema(self) -> Dict[str, Any]:
        """Return part-specific schema properties."""
        sub = self.schema["parts"]["patternProperties"]
        properties = sub["^(?!plugins$)[a-z0-9][a-z0-9+-]*$"]["properties"]
        return properties

    @property
    def definitions_schema(self):
        """Return sub-schema that describes definitions used within schema."""
        return self._schema["definitions"].copy()

    def _load_schema(self, filename: Union[str, Path]) -> None:
        try:
            with open(filename) as schema_file:
                self._schema = json.load(schema_file)
        except FileNotFoundError as err:
            raise errors.SchemaNotFound(filename) from err

    def validate(self, data: Dict[str, Any]) -> None:
        """Validate the given data against the validator's schema.

        :param data: The structured data to validate against the schema.
        """
        validate_schema(data=data, schema=self._schema)

    def merge_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Update the supplied schema with data from the validator schema.

        :param schema: The schema to update.

        :returns: The updated schema.
        """
        schema = copy.deepcopy(schema)

        if "properties" not in schema:
            schema["properties"] = {}

        if "definitions" not in schema:
            schema["definitions"] = {}

        # The part schema takes precedence over the plugin's schema.
        schema["properties"].update(self.part_schema)
        schema["definitions"].update(self.definitions_schema)

        return schema

    def expand_part_properties(self, part_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return properties with all part schema properties included.

        Any schema properties not set will contain their default value as defined
        in the schema itself.

        :param part_properties: The part properties to expand.

        :returns: a dictionary containing all part schema properties.
        """
        # First make a deep copy of the part schema. It contains nested mutables,
        # and we'd rather not change them.
        part_schema = copy.deepcopy(self.part_schema)

        # Come up with a dictionary of part schema properties and their default
        # values as defined in the schema.
        properties = {}
        for schema_property, subschema in part_schema.items():
            properties[schema_property] = subschema.get("default")

        # Now expand (overwriting if necessary) the default schema properties with
        # the ones from the actual part.
        properties.update(part_properties)

        return properties


def validate_schema(*, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate properties according to the given schema.

    :param data: The structured data to validate against the schema.
    :param schema: The validation schema.
    """
    format_check = jsonschema.FormatChecker()
    try:
        jsonschema.validate(data, schema, format_checker=format_check)
    except jsonschema.ValidationError as err:
        raise errors.SchemaValidationError.from_validation_error(err)
