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

from pathlib import Path

import pytest

from craft_parts import errors


def test_parts_error_brief():
    err = errors.PartsError(brief="A brief description.")
    assert str(err) == "A brief description."
    assert (
        repr(err)
        == "PartsError(brief='A brief description.', details=None, resolution=None)"
    )
    assert err.brief == "A brief description."
    assert err.details is None
    assert err.resolution is None


def test_parts_error_full():
    err = errors.PartsError(brief="Brief", details="Details", resolution="Resolution")
    assert str(err) == "Brief\nDetails\nResolution"
    assert (
        repr(err)
        == "PartsError(brief='Brief', details='Details', resolution='Resolution')"
    )
    assert err.brief == "Brief"
    assert err.details == "Details"
    assert err.resolution == "Resolution"


def test_part_dependency_cycle():
    err = errors.PartDependencyCycle()
    assert err.brief == "A circular dependency chain was detected."
    assert err.details is None
    assert err.resolution == "Review the parts definition to remove dependency cycles."


def test_invalid_part_name():
    err = errors.InvalidPartName("foo")
    assert err.part_name == "foo"
    assert err.brief == "A part named 'foo' is not defined in the parts list."
    assert err.details is None
    assert err.resolution == "Review the parts definition and make sure it's correct."


def test_invalid_architecture():
    err = errors.InvalidArchitecture("m68k")
    assert err.arch_name == "m68k"
    assert err.brief == "Architecture 'm68k' is not supported."
    assert err.details is None
    assert err.resolution == "Make sure the architecture name is correct."


@pytest.mark.parametrize("schema_file", ["/some/path", Path("/some/path")])
def test_schema_not_found(schema_file):
    err = errors.SchemaNotFound(schema_file)
    assert err.brief == "Unable to find the schema definition file '/some/path'."
    assert err.resolution == "Make sure craft-parts is correctly installed."


def test_schema_validation_error():
    err = errors.SchemaValidationError("validation failed")
    assert err.brief == "Schema validation error."
    assert err.details == "validation failed"
    assert (
        err.resolution
        == "Review the YAML file and make sure it conforms to the schema."
    )
