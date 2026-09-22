# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

import re

import pydantic
import pytest
from craft_parts.constraints import (
    CHISEL_SLICE_PATTERN,
    MESSAGE_INVALID_CHISEL_SLICE,
    ChiselSliceStr,
    RelativePathStr,
)

_slice_type_adapter = pydantic.TypeAdapter(ChiselSliceStr)
_relative_path_type_adapter = pydantic.TypeAdapter(RelativePathStr)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("file.txt", id="simple"),
        pytest.param("relative/path", id="nested"),
        pytest.param("a", id="single-character"),
    ],
)
def test_relative_path_str_valid(path):
    """Test that valid relative paths are accepted."""
    assert _relative_path_type_adapter.validate_python(path) == path


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("", id="empty-string"),
        pytest.param("/absolute/path", id="absolute-path"),
        pytest.param("/", id="root"),
    ],
)
def test_relative_path_str_invalid(path):
    """Test that invalid relative paths are rejected."""
    with pytest.raises(pydantic.ValidationError):
        _relative_path_type_adapter.validate_python(path)


def test_relative_path_str_json_schema():
    """Ensure the JSON schema is correct."""
    schema = _relative_path_type_adapter.json_schema()

    assert schema["type"] == "string"
    assert schema["description"] == "relative path"
    assert schema["pattern"] == r"^[^\/].*"
    assert schema["minLength"] == 1


@pytest.mark.parametrize(
    "slice_name",
    [
        pytest.param("bash_bins", id="simple"),
        pytest.param("openssl_data", id="simple-2"),
        pytest.param("ca-certificates_data", id="hyphenated-name"),
        pytest.param("libc6_libs", id="digits"),
        pytest.param("libc6.1-dev_libs", id="dots-and-hyphens"),
        pytest.param("g++_bins", id="plus-sign"),
        pytest.param("python3.14_standard", id="dots-and-digits"),
        pytest.param("ab_abc", id="shortest-valid-name"),
        pytest.param("a1_abc", id="starting-with-letter-then-digit"),
    ],
)
def test_chisel_slice_str_valid(slice_name):
    """Test that valid Chisel slice references are accepted."""
    assert _slice_type_adapter.validate_python(slice_name) == slice_name


@pytest.mark.parametrize(
    "slice_name",
    [
        pytest.param("bash", id="missing-slice-name"),
        pytest.param("", id="empty-string"),
        pytest.param("BASH_bins", id="uppercase-package-name"),
        pytest.param("bash_BINS", id="uppercase-slice-name"),
        pytest.param("bash_bi", id="slice-name-shorter-than-3-characters"),
        pytest.param("ab_ab", id="slice-name-shorter-than-3-characters-2"),
        pytest.param("bash_1bins", id="slice-name-starting-with-digit"),
        pytest.param("foo_bar_baz", id="more-than-one-underscore"),
        pytest.param("_bins", id="missing-package-name"),
        pytest.param("bash_", id="missing-slice-name-2"),
        pytest.param("bash__bins", id="double-underscore"),
        pytest.param("-bash_bins", id="package-name-starting-with-hyphen"),
        pytest.param("bash_-bins", id="slice-name-starting-with-hyphen"),
        pytest.param("bash-_bins", id="package-name-ending-with-hyphen"),
    ],
)
def test_chisel_slice_str_invalid(slice_name):
    """Test that invalid Chisel slice references are rejected."""
    with pytest.raises(
        pydantic.ValidationError, match=re.escape(MESSAGE_INVALID_CHISEL_SLICE)
    ):
        _slice_type_adapter.validate_python(slice_name)


def test_chisel_slice_str_json_schema():
    """Ensure the JSON schema is correct."""
    schema = _slice_type_adapter.json_schema()

    assert schema["type"] == "string"
    assert schema["description"] == "Chisel slice reference"
    assert schema["pattern"] == CHISEL_SLICE_PATTERN
