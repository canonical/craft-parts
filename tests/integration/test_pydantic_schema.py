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
"""Integration tests for pydantic schemas."""

from __future__ import annotations

import pathlib

import jsonschema
import pytest
import yaml
from craft_parts import pydantic_schema


class ExamplePartsFile(pydantic_schema.PartsFile):
    description: str


@pytest.fixture(scope="module")
def validator():
    return jsonschema.Draft202012Validator(ExamplePartsFile.model_json_schema())


@pytest.mark.parametrize(
    "path", sorted((pathlib.Path(__file__).parent / "parts_data").glob("*_valid.yaml"))
)
def test_load_valid_parts_file(validator: jsonschema.Validator, path: pathlib.Path):
    parts_data = yaml.safe_load(path.read_text())

    validator.validate(parts_data)
    ExamplePartsFile.model_validate(parts_data)
