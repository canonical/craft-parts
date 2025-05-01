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
"""Tests for pydantic schemas."""

from __future__ import annotations

import jsonschema
import pydantic
import pytest
from craft_parts import pydantic_schema
from craft_parts.plugins import plugins

VALID_PLUGIN_DATAS = [
    *(
        pytest.param({"plugin": plugin}, id=f"plugin_{plugin}")
        for plugin in plugins.get_registered_plugins()
    ),
    {
        "plugin": "ant",
        "ant-build-targets": ["anthill"],
        "ant-build-file": "buildme.ant",
        "ant-properties": {"parts": "head,thorax,abdomen"},
    },
    {
        "plugin": "autotools",
        "autotools-configure-parameters": ["magic"],
        "autotools-bootstrap-parameters": ["shoelaces"],
    },
    {"plugin": "rust", "rust-features": ["abc", "def"]},
]
VALID_SOURCE_DATAS = [
    {
        "source-type": "deb",
        "source": "https://example.com/example.deb",
        "source-checksum": "sha256:blah",
    },
    {"source-type": "git", "source": "git@github.com/canonical/craft-parts"},
    {"source-type": "git", "source": "git+ssh://github.com/canonical/craft-parts"},
    {"source-type": "git", "source": "https://github.com/canonical/craft-parts.git"},
    {"source-type": "local", "source": "."},
    {"source-type": "local", "source": "./"},
    {"source-type": "rpm", "source": "https://example.com/example.rpm"},
    {"source-type": "7z", "source": "https://example.com/example.7z"},
    {"source-type": "snap", "source": "https://example.com/example.snap"},
    {"source-type": "tar", "source": "https://example.com/example.tar"},
    {"source-type": "tar", "source": "https://example.com/example.tar.xz"},
    {"source-type": "tar", "source": "https://example.com/example.tgz"},
    {"source-type": "zip", "source": "https://example.com/example.zip"},
]
VALID_EXPLICIT_SOURCE_DATAS = [  # Source data that is only valid as an explicit source.
    {"source-type": "file", "source": "some_file"},
    {"source-type": "deb", "source": "https://example.com/example.deb?key=value"},
    {"source-type": "git", "source": "user@git.kernel.org/linux"},
    {
        "source-type": "git",
        "source": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux/",
    },
    *(
        {"source-type": source_type, "source": "blah"}
        for source_type in ("deb", "git", "local", "rpm", "7z", "snap", "tar", "zip")
    ),
]

INVALID_PART_DATAS = [
    None,
    pytest.param(
        {"plugin": "nil", "nil-extra-property": "invalid"}, id="nil-extra-property"
    ),
    pytest.param({"plugin": "dump"}, id="missing-source"),
    pytest.param(
        {"plugin": "nil", "source": ".", "source-branch": "invalid"},
        id="branch-on-local-source",
    ),
    pytest.param(
        {"plugin": "nil", "source-type": "git", "source": ".", "source-checksum": ""},
        id="checksum-on-git-source",
    ),
]


@pytest.fixture(scope="module")
def part_schema():
    return pydantic_schema.Part.model_json_schema()


@pytest.fixture(scope="module")
def validator(part_schema):
    return jsonschema.Draft202012Validator(part_schema)


@pytest.mark.parametrize("plugin_data", VALID_PLUGIN_DATAS)
@pytest.mark.parametrize(
    "source_data", VALID_SOURCE_DATAS + VALID_EXPLICIT_SOURCE_DATAS
)
def test_valid_part_schema(validator, plugin_data, source_data):
    part_data = plugin_data | source_data
    validator.validate(part_data)
    part = pydantic_schema.Part.model_validate(part_data)

    assert part.plugin_data.plugin == part_data["plugin"]


@pytest.mark.parametrize("plugin_data", VALID_PLUGIN_DATAS)
@pytest.mark.parametrize("source_data", VALID_SOURCE_DATAS)
def test_part_schema_implicit_source_type(validator, plugin_data, source_data):
    part_data = plugin_data | source_data
    source_type = part_data.pop("source-type")
    validator.validate(part_data)
    part = pydantic_schema.Part.model_validate(part_data)

    assert part.source_data.source_type == source_type


@pytest.mark.parametrize("part_data", INVALID_PART_DATAS)
def test_invalid_part_data(validator, part_data):
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(part_data)

    with pytest.raises(pydantic.ValidationError):
        pydantic_schema.Part.model_validate(part_data)
