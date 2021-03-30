# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import json
import textwrap
from pathlib import Path

import pytest

from craft_parts import errors, schemas
from craft_parts.schemas import Validator
from tests import TESTS_DIR

_SCHEMA_DIR = TESTS_DIR.parent / "craft_parts" / "data" / "schema"


class TestValidateSchema:
    """Schema validation tests."""

    _schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "data": {
                "type": "string",
            },
        },
        "required": ["data"],
    }

    def test_validate_schema(self):
        data = {"data": "value"}
        schemas.validate_schema(data=data, schema=TestValidateSchema._schema)

    def test_validate_schema_error(self):
        data = {}
        with pytest.raises(errors.SchemaValidationError) as raised:
            schemas.validate_schema(data=data, schema=TestValidateSchema._schema)
        assert raised.value.details == "'data' is a required property"


class TestValidator:
    """Validator tests with generic schema."""

    _schema_json = textwrap.dedent(
        """
        {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "additionalProperties": { "enum": [ false ] },
            "properties": {
                "data": {
                    "type": "string"
                 }
            },
            "required": ["data"]
        }
        """
    )

    @pytest.mark.usefixtures("new_dir")
    def test_validator(self):
        Path("schema.json").write_text(TestValidator._schema_json)
        validator = Validator("schema.json")

        validator.validate({"data": "value"})

        assert validator.schema == {"data": {"type": "string"}}

    def test_validator_invalid_filename(self):
        with pytest.raises(errors.SchemaNotFound) as raised:
            Validator("does_not_exist.json")
        assert raised.value.path == "does_not_exist.json"


class TestPartsValidation:
    """Validator tests with parts schema."""

    @pytest.mark.parametrize(
        "name", ["plugins", "qwe#rty", "qwe_rty", "queue rty", "queue  rty", "part/sub"]
    )
    def test_invalid_part_names(self, name):
        validator = Validator(_SCHEMA_DIR / "parts.json")
        data = {"parts": {name: {"plugin": "nil"}}}

        with pytest.raises(errors.SchemaValidationError) as raised:
            validator.validate(data)

        expected_message = (
            f"The 'parts' property does not match the required schema: {name!r} is "
            "not a valid part name. Part names consist of lower-case "
            "alphanumeric characters, hyphens and plus signs. "
            "As a special case, 'plugins' is also not a valid part name."
        )
        assert raised.value.details.endswith(expected_message)

    def test_part_schema(self):
        validator = Validator(_SCHEMA_DIR / "parts.json")

        with open(_SCHEMA_DIR / "parts.json") as f:
            schema = json.load(f)

        pattern_properties = schema["properties"]["parts"]["patternProperties"]
        properties = pattern_properties["^(?!plugins$)[a-z0-9][a-z0-9+-]*$"][
            "properties"
        ]

        assert validator.part_schema == properties

    def test_definitions_schema(self):
        validator = Validator(_SCHEMA_DIR / "parts.json")

        with open(_SCHEMA_DIR / "parts.json") as f:
            schema = json.load(f)

        assert validator.definitions_schema == schema["definitions"]

    def test_merge_schemas_trivial(self):
        validator = Validator(_SCHEMA_DIR / "parts.json")
        merged = validator.merge_schema({})

        assert merged["properties"] == validator.part_schema
        assert merged["definitions"] == validator.definitions_schema

    def test_merge_schemas(self):
        validator = Validator(_SCHEMA_DIR / "parts.json")

        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "more-properties": {"type": "string"},
            },
            "definitions": {
                "more-definitions": "value",
            },
        }

        merged = validator.merge_schema(schema)

        # make sure we're not modifying the original schema data
        assert merged != schema

        schema["properties"].update(validator.part_schema)
        schema["definitions"].update(validator.definitions_schema)

        assert merged == schema

    def test_expand_part_properties(self):
        validator = Validator(_SCHEMA_DIR / "parts.json")
        expanded = validator.expand_part_properties(
            {
                "after": ["foo", "bar"],
                "new-property": "some value",
            }
        )

        assert expanded == {
            "after": ["foo", "bar"],
            "build-attributes": [],
            "build-environment": [],
            "build-packages": [],
            "build-snaps": [],
            "disable-parallel": False,
            "filesets": {},
            "new-property": "some value",
            "organize": {},
            "override-build": None,
            "override-prime": None,
            "override-pull": None,
            "override-stage": None,
            "parse-info": [],
            "plugin": None,
            "prime": ["*"],
            "source": None,
            "source-branch": "",
            "source-checksum": "",
            "source-commit": "",
            "source-depth": 0,
            "source-subdir": "",
            "source-tag": "",
            "source-type": "",
            "stage": ["*"],
            "stage-packages": [],
            "stage-snaps": [],
        }
