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


def test_part_specification_error():
    err = errors.PartSpecificationError(part_name="foo", message="something is wrong")
    assert err.part_name == "foo"
    assert err.brief == "Part 'foo' validation failed."
    assert err.details == "something is wrong"
    assert err.resolution == "Review part 'foo' and make sure it's correct."


def test_part_specification_error_from_validation_error():
    error_list = [
        {"loc": ("field-1",), "msg": "something is wrong"},
        {"loc": ("field-2",), "msg": "something is wrong"},
    ]
    err = errors.PartSpecificationError.from_validation_error(
        part_name="foo", error_list=error_list
    )
    assert err.part_name == "foo"
    assert err.brief == "Part 'foo' validation failed."
    assert err.details == "'field-1': something is wrong\n'field-2': something is wrong"
    assert err.resolution == "Review part 'foo' and make sure it's correct."


def test_part_specification_error_from_bad_validation_error():
    error_list = [
        {"loc": "field-1", "msg": "something is wrong"},
        {"loc": "field-1"},
        {"msg": "something is wrong"},
        {},
    ]
    err = errors.PartSpecificationError.from_validation_error(
        part_name="foo", error_list=error_list
    )
    assert err.part_name == "foo"
    assert err.brief == "Part 'foo' validation failed."
    assert err.details == ""
    assert err.resolution == "Review part 'foo' and make sure it's correct."


def test_copy_tree_error():
    err = errors.CopyTreeError("something bad happened")
    assert err.message == "something bad happened"
    assert err.brief == "Failed to copy or link file tree: something bad happened."
    assert err.details is None
    assert err.resolution == "Make sure paths and permissions are correct."


def test_copy_file_not_found():
    err = errors.CopyFileNotFound("filename")
    assert err.name == "filename"
    assert err.brief == "Failed to copy 'filename': no such file or directory."
    assert err.details is None
    assert err.resolution is None


def test_xattribute_read_error():
    err = errors.XAttributeError(key="name", path="path")
    assert err.key == "name"
    assert err.path == "path"
    assert err.is_write is False
    assert err.brief == "Unable to read extended attribute."
    assert err.details == "Failed to read attribute 'name' on 'path'."
    assert err.resolution == "Make sure your filesystem supports extended attributes."


def test_xattribute_write_error():
    err = errors.XAttributeError(key="name", path="path", is_write=True)
    assert err.key == "name"
    assert err.path == "path"
    assert err.is_write is True
    assert err.brief == "Unable to write extended attribute."
    assert err.details == "Failed to write attribute 'name' on 'path'."
    assert err.resolution == "Make sure your filesystem supports extended attributes."


def test_undefined_plugin():
    err = errors.UndefinedPlugin(part_name="foo")
    assert err.part_name == "foo"
    assert err.brief == "Plugin not defined for part 'foo'."
    assert err.details is None
    assert err.resolution == "Review part 'foo' and make sure it's correct."


def test_invalid_plugin():
    err = errors.InvalidPlugin("name", part_name="foo")
    assert err.plugin_name == "name"
    assert err.part_name == "foo"
    assert err.brief == "Plugin 'name' in part 'foo' is not registered."
    assert err.details is None
    assert err.resolution == "Review part 'foo' and make sure it's correct."
