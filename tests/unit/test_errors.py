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

from typing import TYPE_CHECKING

from craft_parts import errors

if TYPE_CHECKING:
    from pydantic.error_wrappers import ErrorDict


def test_parts_error_brief():
    err = errors.PartsError(brief="A brief description.")
    assert str(err) == "A brief description."
    assert (
        repr(err)
        == "PartsError(brief='A brief description.', details=None, resolution=None, doc_slug=None)"
    )
    assert err.brief == "A brief description."
    assert err.details is None
    assert err.resolution is None


def test_parts_error_full():
    err = errors.PartsError(brief="Brief", details="Details", resolution="Resolution")
    assert str(err) == "Brief\nDetails\nResolution"
    assert (
        repr(err)
        == "PartsError(brief='Brief', details='Details', resolution='Resolution', doc_slug=None)"
    )
    assert err.brief == "Brief"
    assert err.details == "Details"
    assert err.resolution == "Resolution"


def test_part_dependency_cycle():
    err = errors.PartDependencyCycle()
    assert err.brief == "A circular dependency chain was detected."
    assert err.details is None
    assert err.resolution == "Review the parts definition to remove dependency cycles."


def test_feature():
    err = errors.FeatureError("bummer")
    assert err.message == "bummer"
    assert err.brief == "bummer"
    assert err.details is None
    assert err.resolution == "This operation cannot be executed."


def test_feature_with_details():
    err = errors.FeatureError(message="bummer", details="test details")
    assert err.message == "bummer"
    assert err.brief == "bummer"
    assert err.details == "test details"
    assert err.resolution == "This operation cannot be executed."


def test_invalid_application_name():
    err = errors.InvalidApplicationName("foo")
    assert err.name == "foo"
    assert err.brief == "Application name 'foo' is invalid."
    assert err.details is None
    assert err.resolution == (
        "Valid application names contain letters, underscores or numbers, "
        "and must start with a letter."
    )


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


def test_part_specification_error_from_validation_error() -> None:
    error_list: list[ErrorDict] = [
        {"loc": ("field-1", 0), "msg": "something is wrong", "type": "value_error"},
        {"loc": ("field-2",), "msg": "field required", "type": "value_error"},
        {
            "loc": ("field-3",),
            "msg": "extra fields not permitted",
            "type": "value_error",
        },
    ]
    err = errors.PartSpecificationError.from_validation_error(
        part_name="foo", error_list=error_list
    )
    assert err.part_name == "foo"
    assert err.brief == "Part 'foo' validation failed."
    assert err.details == (
        "- something is wrong in field 'field-1[0]'\n"
        "- field 'field-2' is required\n"
        "- extra field 'field-3' not permitted"
    )
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


def test_os_release_id_error():
    err = errors.OsReleaseIdError()
    assert err.brief == "Unable to determine the host operating system ID."
    assert err.details is None
    assert err.resolution is None


def test_os_release_name_error():
    err = errors.OsReleaseNameError()
    assert err.brief == "Unable to determine the host operating system name."
    assert err.details is None
    assert err.resolution is None


def test_os_release_version_id_error():
    err = errors.OsReleaseVersionIdError()
    assert err.brief == "Unable to determine the host operating system version ID."
    assert err.details is None
    assert err.resolution is None


def test_os_release_codename_error():
    err = errors.OsReleaseCodenameError()
    assert err.brief == "Unable to determine the host operating system codename."
    assert err.details is None
    assert err.resolution is None


def test_fileset_error():
    err = errors.FilesetError(name="stage", message="something is wrong")
    assert err.name == "stage"
    assert err.message == "something is wrong"
    assert err.brief == "'stage' fileset error: something is wrong."
    assert err.details is None
    assert err.resolution == "Review the parts definition and make sure it's correct."


def test_fileset_conflict():
    err = errors.FilesetConflict({"foobar"})
    assert err.conflicting_files == {"foobar"}
    assert err.brief == (
        "Failed to filter files: inconsistent 'stage' and 'prime' filesets."
    )
    assert err.details == (
        "The following files have been excluded in the 'stage' fileset, "
        "but included by the 'prime' fileset: {'foobar'}."
    )
    assert err.resolution == (
        "Make sure that the files included in 'prime' are also included in 'stage'."
    )


def test_file_organize_error():
    err = errors.FileOrganizeError(part_name="foo", message="not ready reading drive A")
    assert err.part_name == "foo"
    assert err.message == "not ready reading drive A"
    assert err.brief == "Failed to organize part 'foo': not ready reading drive A."
    assert err.details is None
    assert err.resolution is None


def test_part_files_conflict():
    err = errors.PartFilesConflict(
        part_name="foo", other_part_name="bar", conflicting_files=["file1", "file2"]
    )
    assert err.part_name == "foo"
    assert err.other_part_name == "bar"
    assert err.conflicting_files == ["file1", "file2"]
    assert err.brief == (
        "Failed to stage: parts list the same file with different contents or permissions."
    )
    assert err.details == (
        "Parts 'foo' and 'bar' list the following files, "
        "but with different contents or permissions:\n"
        "    file1\n"
        "    file2"
    )
    assert err.resolution is None


def test_part_files_conflict_with_partitions():
    """Test PartsFilesConflict with a partition."""
    err = errors.PartFilesConflict(
        part_name="foo",
        other_part_name="bar",
        conflicting_files=["file1", "file2"],
        partition="test",
    )
    assert err.part_name == "foo"
    assert err.other_part_name == "bar"
    assert err.conflicting_files == ["file1", "file2"]
    assert err.partition == "test"
    assert err.brief == (
        "Failed to stage: parts list the same file with different contents or permissions."
    )
    assert err.details == (
        "Parts 'foo' and 'bar' list the following files for the 'test' partition, "
        "but with different contents or permissions:\n"
        "    file1\n"
        "    file2"
    )
    assert err.resolution is None


def test_stage_files_conflict():
    err = errors.StageFilesConflict(
        part_name="foo", conflicting_files=["file1", "file2"]
    )
    assert err.part_name == "foo"
    assert err.conflicting_files == ["file1", "file2"]
    assert err.brief == (
        "Failed to stage: part files conflict with files already being staged."
    )
    assert err.details == (
        "The following files in part 'foo' are already being staged with different "
        "content:\n"
        "    file1\n"
        "    file2"
    )
    assert err.resolution is None


def test_plugin_environment_validation_error():
    err = errors.PluginEnvironmentValidationError(
        part_name="foo", reason="compiler not found"
    )
    assert err.part_name == "foo"
    assert err.reason == "compiler not found"
    assert err.brief == (
        "Environment validation failed for part 'foo': compiler not found."
    )
    assert err.details is None
    assert err.resolution is None


def test_plugin_build_error():
    err = errors.PluginBuildError(part_name="foo", plugin_name="go")
    assert err.part_name == "foo"
    assert err.plugin_name == "go"
    assert err.brief == "Failed to run the build script for part 'foo'."
    assert err.details is None
    assert (
        err.resolution
        == "Check the build output and verify the project can work with the 'go' plugin."
    )
    assert err.doc_slug == "/reference/plugins.html"


def test_invalid_control_api_call():
    err = errors.InvalidControlAPICall(
        part_name="foo", scriptlet_name="override-build", message="everything is broken"
    )
    assert err.part_name == "foo"
    assert err.scriptlet_name == "override-build"
    assert err.message == "everything is broken"
    assert err.brief == (
        "'override-build' in part 'foo' executed an invalid control API call: "
        "everything is broken."
    )
    assert err.details is None
    assert err.resolution == "Review the scriptlet and make sure it's correct."


def test_scriptlet_run_error():
    err = errors.ScriptletRunError(
        part_name="foo", scriptlet_name="override-build", exit_code=42
    )
    assert err.part_name == "foo"
    assert err.scriptlet_name == "override-build"
    assert err.exit_code == 42
    assert err.brief == "'override-build' in part 'foo' failed with code 42."
    assert err.details is None
    assert err.resolution == "Review the scriptlet and make sure it's correct."


def test_callback_registration_error():
    err = errors.CallbackRegistrationError("General failure reading drive A")
    assert err.message == "General failure reading drive A"
    assert err.brief == "Callback registration error: General failure reading drive A."
    assert err.details is None
    assert err.resolution is None


def test_stage_package_not_found():
    err = errors.StagePackageNotFound(part_name="foo", package_name="figlet")
    assert err.part_name == "foo"
    assert err.package_name == "figlet"
    assert err.brief == "Stage package not found in part 'foo': figlet."
    assert err.details is None
    assert err.resolution is None


def test_overlay_package_not_found():
    err = errors.OverlayPackageNotFound(part_name="foo", package_name="figlet")
    assert err.part_name == "foo"
    assert err.package_name == "figlet"
    assert err.brief == "Overlay package not found in part 'foo': figlet."
    assert err.details is None
    assert err.resolution is None


def test_invalid_action():
    err = errors.InvalidAction("cannot update step 'stage'")
    assert err.message == "cannot update step 'stage'"
    assert err.brief == "Action is invalid: cannot update step 'stage'."
    assert err.details is None
    assert err.resolution is None


def test_overlay_platform_error():
    err = errors.OverlayPlatformError()
    assert err.brief == "The overlay step is only supported on Linux."
    assert err.details is None
    assert err.resolution is None


def test_overlay_permission_error():
    err = errors.OverlayPermissionError()
    assert err.brief == "Using the overlay step requires superuser privileges."
    assert err.details is None
    assert err.resolution is None


class TestPartitionErrors:
    def test_partition_error(self):
        err = errors.PartitionError(
            brief="test brief", details="test details", resolution="test resolution"
        )

        assert err.brief == "test brief"
        assert err.details == "test details"
        assert err.resolution == "test resolution"

    def test_invalid_partition_usage(self):
        err = errors.PartitionUsageError(
            error_list=[
                "  parts.test-part.organize",
                "    unknown partition 'foo' in '(foo)'",
            ],
            partitions=["default", "mypart", "yourpart"],
        )

        assert err.brief == "Invalid usage of partitions"
        assert err.details == (
            "  parts.test-part.organize\n"
            "    unknown partition 'foo' in '(foo)'\n"
            "Valid partitions: default, mypart, yourpart"
        )
        assert err.resolution == "Correct the invalid partition name(s) and try again."

    def test_invalid_partition_warning(self):
        err = errors.PartitionUsageWarning(
            warning_list=[
                "  parts.test-part.organize",
                "    misused partition 'yourpart' in 'yourpart/test-file'",
            ]
        )

        assert err.brief == "Possible misuse of partitions"
        assert err.details == (
            "The following entries begin with a valid partition name but are not "
            "wrapped in parentheses. These entries will go into the "
            "default partition.\n"
            "  parts.test-part.organize\n"
            "    misused partition 'yourpart' in 'yourpart/test-file'"
        )
        assert err.resolution == (
            "Wrap the partition name in parentheses, for example "
            "'default/file' should be written as '(default)/file'"
        )
