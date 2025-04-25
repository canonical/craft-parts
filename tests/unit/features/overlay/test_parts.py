# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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

from copy import deepcopy
from functools import partial

import pydantic
import pytest
from craft_parts import errors, parts
from craft_parts.dirs import ProjectDirs
from craft_parts.packages import platform
from craft_parts.parts import Part, PartSpec
from craft_parts.steps import Step

# pylint: disable=too-many-public-methods


class TestPartSpecs:
    """Test part specification creation and query."""

    def test_marshal_unmarshal(self):
        data = {
            "plugin": "nil",
            "source": "http://example.com/hello-2.3.tar.gz",
            "source-checksum": "md5/d9210476aac5f367b14e513bdefdee08",
            "source-channel": None,
            "source-branch": "release",
            "source-commit": "2514f9533ec9b45d07883e10a561b248497a8e3c",
            "source-depth": 3,
            "source-subdir": "src",
            "source-submodules": ["submodule_1", "dir/submodule_2"],
            "source-tag": "v2.3",
            "source-type": "tar",
            "disable-parallel": True,
            "after": ["bar"],
            "overlay-packages": ["overlay-pkg1", "overlay-pkg2"],
            "stage-snaps": ["stage-snap1", "stage-snap2"],
            "stage-packages": ["stage-pkg1", "stage-pkg2"],
            "build-snaps": ["build-snap1", "build-snap2"],
            "build-packages": ["build-pkg1", "build-pkg2"],
            "build-environment": [{"ENV1": "on"}, {"ENV2": "off"}],
            "build-attributes": ["attr1", "attr2"],
            "organize": {"src1": "dest1", "src2": "dest2"},
            "overlay": ["etc/issue"],
            "stage": ["-usr/docs"],
            "prime": ["*"],
            "override-pull": "override-pull",
            "overlay-script": "overlay-script",
            "override-build": "override-build",
            "override-stage": "override-stage",
            "override-prime": "override-prime",
            "permissions": [
                {"path": "etc/*", "owner": 1111, "group": 1111, "mode": "755"}
            ],
        }

        data_copy = deepcopy(data)

        spec = PartSpec.unmarshal(data)
        assert data == data_copy

        new_data = spec.marshal()
        assert new_data == data_copy

    def test_unmarshal_not_dict(self):
        with pytest.raises(TypeError) as raised:
            PartSpec.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
        assert str(raised.value) == "part data is not a dictionary"

    def test_unmarshal_mix_packages_slices(self, mocker):
        """
        Test that mixing packages and chisel slices raises validation errors
        in Debian-based systems (and only in them).
        """
        is_deb_mock = mocker.patch.object(platform, "is_deb_based", autospec=True)

        package_list = ["pkg1_bin", "pkg2_bin", "pkg3"]
        data = {
            "stage-packages": package_list,
        }

        # On Debian-based systems, mixing names with and without underscores means
        # mixing .deb packages and chisel slices, which is not allowed.
        is_deb_mock.return_value = True
        with pytest.raises(pydantic.ValidationError):
            PartSpec.unmarshal(data)

        # On non-Debian-based systems, mixing is allowed because we can't know the
        # semantics (and chisel is not supported).
        is_deb_mock.return_value = False
        spec = PartSpec.unmarshal(data)
        assert spec.stage_packages == package_list

    @pytest.mark.parametrize(
        ("packages", "script", "files", "result"),
        [
            ([], None, ["*"], False),
            (["pkg"], None, ["*"], True),
            ([], "ls", ["*"], True),
            ([], None, ["-usr/share"], True),
        ],
    )
    def test_spec_has_overlay(self, packages, script, files, result):
        data = {
            "overlay-packages": packages,
            "overlay-script": script,
            "overlay": files,
        }
        spec = PartSpec.unmarshal(data)
        assert spec.has_overlay == result


class TestPartData:
    """Test basic part creation and representation."""

    def test_part_dirs(self, new_dir, partitions):
        p = Part("foo", {"plugin": "nil"}, partitions=partitions)
        assert f"{p!r}" == "Part('foo')"
        assert p.name == "foo"
        assert p.parts_dir == new_dir / "parts"
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build"
        assert p.part_install_dir == new_dir / "parts/foo/install"
        assert p.part_state_dir == new_dir / "parts/foo/state"
        assert p.part_packages_dir == new_dir / "parts/foo/stage_packages"
        assert p.part_snaps_dir == new_dir / "parts/foo/stage_snaps"
        assert p.part_run_dir == new_dir / "parts/foo/run"
        assert p.part_layer_dir == new_dir / "parts/foo/layer"
        assert p.part_cache_dir == new_dir / "parts/foo/cache"
        assert p.overlay_dir == new_dir / "overlay"
        assert p.backstage_dir == new_dir / "backstage"
        assert p.stage_dir == new_dir / "stage"
        assert p.prime_dir == new_dir / "prime"

    def test_part_work_dir(self, new_dir, partitions):
        p = Part(
            "foo",
            {},
            project_dirs=ProjectDirs(work_dir="foobar", partitions=partitions),
            partitions=partitions,
        )
        assert p.parts_dir == new_dir / "foobar/parts"
        assert p.part_src_dir == new_dir / "foobar/parts/foo/src"
        assert p.part_src_subdir == new_dir / "foobar/parts/foo/src"
        assert p.part_build_dir == new_dir / "foobar/parts/foo/build"
        assert p.part_build_subdir == new_dir / "foobar/parts/foo/build"
        assert p.part_install_dir == new_dir / "foobar/parts/foo/install"
        assert p.part_state_dir == new_dir / "foobar/parts/foo/state"
        assert p.part_packages_dir == new_dir / "foobar/parts/foo/stage_packages"
        assert p.part_snaps_dir == new_dir / "foobar/parts/foo/stage_snaps"
        assert p.part_run_dir == new_dir / "foobar/parts/foo/run"
        assert p.part_layer_dir == new_dir / "foobar/parts/foo/layer"
        assert p.overlay_dir == new_dir / "foobar/overlay"
        assert p.backstage_dir == new_dir / "foobar/backstage"
        assert p.stage_dir == new_dir / "foobar/stage"
        assert p.prime_dir == new_dir / "foobar/prime"

    def test_part_subdirs_default(self, new_dir):
        """Verify subdirectories for a part with no plugin."""
        p = Part("foo", {"source-subdir": "foobar"})
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src/foobar"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build"

    def test_part_subdirs_out_of_source_and_source_subdir(self, new_dir):
        """
        Verify subdirectories for a plugin that supports out-of-source builds
        and has a source subdirectory defined.
        """
        p = Part("foo", {"plugin": "cmake", "source-subdir": "foobar"})
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src/foobar"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build"

    def test_part_subdirs_out_of_source(self, new_dir):
        """
        Verify subdirectories for a plugin that supports out-of-source builds
        and no source subdirectory defined.
        """
        p = Part("foo", {"plugin": "cmake"})
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build"

    def test_part_subdirs_source_subdir(self, new_dir):
        """
        Verify subdirectories for a plugin that does not support out-of-source builds
        and has a source subdirectory defined.
        """
        p = Part("foo", {"plugin": "dump", "source-subdir": "foobar"})
        assert p.part_src_dir == new_dir / "parts/foo/src"
        assert p.part_src_subdir == new_dir / "parts/foo/src/foobar"
        assert p.part_build_dir == new_dir / "parts/foo/build"
        assert p.part_build_subdir == new_dir / "parts/foo/build/foobar"

    def test_part_source(self):
        p = Part("foo", {})
        assert p.spec.source is None

        p = Part("foo", {"source": "foobar"})
        assert p.spec.source == "foobar"

    def test_part_stage_files(self):
        p = Part("foo", {"stage": ["a", "b", "c"]})
        assert p.spec.stage_files == ["a", "b", "c"]

    def test_part_prime_files(self):
        p = Part("foo", {"prime": ["a", "b", "c"]})
        assert p.spec.prime_files == ["a", "b", "c"]

    def test_part_organize_files(self):
        p = Part("foo", {"organize": {"a": "b", "c": "d"}})
        assert p.spec.organize_files == {"a": "b", "c": "d"}

    def test_part_dependencies(self):
        p = Part("foo", {"after": ["bar"]})
        assert p.dependencies == ["bar"]

    def test_part_plugin(self):
        p = Part("foo", {"plugin": "nil"})
        assert p.spec.plugin == "nil"

    def test_part_plugin_missing(self):
        p = Part("foo", {})
        assert p.spec.plugin is None

    def test_part_build_environment(self):
        p = Part("foo", {"build-environment": [{"BAR": "bar"}]})
        assert p.spec.build_environment == [{"BAR": "bar"}]

    @pytest.mark.parametrize(
        ("tc_spec", "tc_result"),
        [
            ({}, []),
            ({"stage-packages": []}, []),
            ({"stage-packages": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_stage_packages(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.stage_packages == tc_result

    @pytest.mark.parametrize(
        ("tc_spec", "tc_result"),
        [
            ({}, []),
            ({"stage-snaps": []}, []),
            ({"stage-snaps": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_stage_snaps(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.stage_snaps == tc_result

    @pytest.mark.parametrize(
        ("tc_spec", "tc_result"),
        [
            ({}, []),
            ({"build-packages": []}, []),
            ({"build-packages": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_build_packages(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.build_packages == tc_result

    @pytest.mark.parametrize(
        ("tc_spec", "tc_result"),
        [
            ({}, []),
            ({"build-snaps": []}, []),
            ({"build-snaps": ["foo", "bar"]}, ["foo", "bar"]),
        ],
    )
    def test_part_build_snaps(self, tc_spec, tc_result):
        p = Part("foo", tc_spec)
        assert p.spec.build_snaps == tc_result

    @pytest.mark.parametrize(
        ("tc_step", "tc_content"),
        [
            (Step.PULL, "pull"),
            (Step.OVERLAY, "overlay"),
            (Step.BUILD, "build"),
            (Step.STAGE, "stage"),
            (Step.PRIME, "prime"),
        ],
    )
    def test_part_get_scriptlet(self, tc_step, tc_content):
        p = Part(
            "foo",
            {
                "override-pull": "pull",
                "override-build": "build",
                "override-stage": "stage",
                "override-prime": "prime",
                "overlay-script": "overlay",
            },
        )
        assert p.spec.get_scriptlet(tc_step) == tc_content

    @pytest.mark.parametrize("step", list(Step))
    def test_part_get_scriptlet_none(self, step):
        p = Part("foo", {})
        assert p.spec.get_scriptlet(step) is None

    @pytest.mark.parametrize(
        ("packages", "script", "files", "result"),
        [
            ([], None, ["*"], False),
            (["pkg"], None, ["*"], True),
            ([], "ls", ["*"], True),
            ([], None, ["-usr/share"], True),
        ],
    )
    def test_part_has_overlay(self, packages, script, files, result):
        p = Part(
            "foo",
            {
                "overlay-packages": packages,
                "overlay-script": script,
                "overlay": files,
            },
        )
        assert p.has_overlay == result


class TestPartOrdering:
    """Test part ordering.

    Parts should be ordered primarily by dependencies, and then by
    part name.
    """

    def test_sort_parts(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["foo"]})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p1, p3, p2]

    def test_sort_parts_multiple(self):
        p1 = Part("foo", {"after": ["bar", "baz"]})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p3, p2, p1]

    def test_sort_parts_name(self):
        p1 = Part("baz", {"after": ["foo"]})
        p2 = Part("bar", {"after": ["foo"]})
        p3 = Part("foo", {})

        x = parts.sort_parts([p1, p2, p3])
        assert x == [p3, p2, p1]

    def test_sort_parts_cycle(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["bar"]})

        with pytest.raises(errors.PartDependencyCycle):
            parts.sort_parts([p1, p2, p3])


class TestPartUnmarshal:
    """Verify data unmarshaling on part creation."""

    def test_part_valid_property(self):
        data = {"plugin": "nil"}
        Part("foo", data)
        assert data == {"plugin": "nil"}

    def test_part_unexpected_property(self):
        data = {"a": 2, "b": 3}
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", data)
        assert raised.value.part_name == "foo"
        assert raised.value.message == (
            "- Extra inputs are not permitted in field 'a'\n"
            "- Extra inputs are not permitted in field 'b'"
        )

    def test_part_spec_not_dict(self):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
        assert raised.value.part_name == "foo"
        assert raised.value.message == "part data is not a dictionary"

    def test_part_unmarshal_type_error(self):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", {"plugin": []})
        assert raised.value.part_name == "foo"
        assert (
            raised.value.message == "- Input should be a valid string in field 'plugin'"
        )

    @pytest.mark.parametrize("fileset", ["stage", "prime"])
    def test_relative_path_validation(self, fileset):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", {fileset: ["bar", "/baz", ""]})
        assert raised.value.part_name == "foo"
        assert raised.value.message == (
            "- Value error, '/baz' must be a relative path (cannot start with '/') "
            f"in field '{fileset}[1]'\n"
            f"- Value error, path cannot be empty in field '{fileset}[2]'"
        )


class TestPartHelpers:
    """Test part-related helper functions."""

    def test_part_by_name(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})
        p3 = Part("baz", {})

        x = parts.part_by_name("bar", [p1, p2, p3])
        assert x == p2

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_by_name("invalid", [p1, p2, p3])
        assert raised.value.part_name == "invalid"

    def test_part_list_by_name(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {})
        p3 = Part("baz", {})

        x = parts.part_list_by_name(["bar", "baz"], [p1, p2, p3])
        assert x == [p2, p3]

        x = parts.part_list_by_name(("bar", "baz"), [p1, p2, p3])
        assert x == [p2, p3]

        # If the list is empty or not defined, return all parts
        x = parts.part_list_by_name([], [p1, p2, p3])
        assert x == [p1, p2, p3]

        x = parts.part_list_by_name(None, [p1, p2, p3])
        assert x == [p1, p2, p3]

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_list_by_name(["bar", "invalid"], [p1, p2, p3])
        assert raised.value.part_name == "invalid"

    def test_part_dependencies(self):
        p1 = Part("foo", {"after": ["bar", "baz"]})
        p2 = Part("bar", {"after": ["qux"]})
        p3 = Part("baz", {})
        p4 = Part("qux", {})

        x = parts.part_dependencies(p1, part_list=[p1, p2, p3, p4])
        assert x == {p2, p3}

        x = parts.part_dependencies(p1, part_list=[p1, p2, p3, p4], recursive=True)
        assert x == {p2, p3, p4}

    def test_has_overlay_visibility(self):
        p1 = Part("foo", {"after": ["bar", "baz"]})
        p2 = Part("bar", {"after": ["qux"]})
        p3 = Part("baz", {})
        p4 = Part("qux", {"overlay-script": "echo"})
        p5 = Part("foobar", {"after": ["baz"]})

        part_list = [p1, p2, p3, p4, p5]

        has_overlay_visibility = partial(
            parts.has_overlay_visibility, viewers=set(), part_list=part_list
        )

        assert has_overlay_visibility(p1) is True
        assert has_overlay_visibility(p2) is True
        assert has_overlay_visibility(p3) is False
        assert has_overlay_visibility(p4) is True
        assert has_overlay_visibility(p5) is False

    def test_get_parts_with_overlay(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"overlay-packages": ["pkg1"]})
        p3 = Part("baz", {"overlay-script": "echo"})
        p4 = Part("qux", {"overlay": ["*"]})
        p5 = Part("quux", {"overlay": ["-etc/passwd"]})

        p = parts.get_parts_with_overlay(part_list=[p1, p2, p3, p4, p5])
        assert p == [p2, p3, p5]

    @pytest.mark.parametrize(
        ("packages", "script", "files", "result"),
        [
            ([], None, ["*"], False),
            (["pkg"], None, ["*"], True),
            ([], "ls", ["*"], True),
            ([], None, ["-usr/share"], True),
        ],
    )
    def test_part_has_overlay(self, packages, script, files, result):
        data = {
            "plugin": "nil",
            "overlay-packages": packages,
            "overlay-script": script,
            "overlay": files,
        }
        assert parts.part_has_overlay(data) == result


class TestPartValidation:
    """Part validation considering plugin-specific attributes."""

    def test_part_validation_data_type(self):
        with pytest.raises(TypeError) as raised:
            parts.validate_part("invalid data")  # type: ignore[reportGeneralTypeIssues]

        assert str(raised.value) == "value must be a dictionary"

    def test_part_validation_immutable(self):
        data = {
            "plugin": "make",
            "source": "foo",
            "make-parameters": ["-C bar"],
        }
        data_copy = deepcopy(data)

        parts.validate_part(data)

        assert data == data_copy

    def test_part_validation_extra(self):
        data = {
            "plugin": "make",
            "source": "foo",
            "make-parameters": ["-C bar"],
            "unexpected-extra": True,
        }

        error = r"unexpected-extra\s+Extra inputs are not permitted"
        with pytest.raises(pydantic.ValidationError, match=error):
            parts.validate_part(data)

    def test_part_validation_missing(self):
        data = {
            "plugin": "make",
            "make-parameters": ["-C bar"],
        }

        error = r"source\s+Field required"
        with pytest.raises(pydantic.ValidationError, match=error):
            parts.validate_part(data)
