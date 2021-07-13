# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import pytest

from craft_parts import errors, parts
from craft_parts.dirs import ProjectDirs
from craft_parts.parts import Part, PartSpec
from craft_parts.steps import Step


class TestPartSpecs:
    """Test part specification creation."""

    def test_marshal_unmarshal(self):
        data = {
            "plugin": "nil",
            "source": "http://example.com/hello-2.3.tar.gz",
            "source-checksum": "md5/d9210476aac5f367b14e513bdefdee08",
            "source-branch": "release",
            "source-commit": "2514f9533ec9b45d07883e10a561b248497a8e3c",
            "source-depth": 3,
            "source-subdir": "src",
            "source-tag": "v2.3",
            "source-type": "tar",
            "disable-parallel": True,
            "after": ["bar"],
            "stage-snaps": ["stage-snap1", "stage-snap2"],
            "stage-packages": ["stage-pkg1", "stage-pkg2"],
            "build-snaps": ["build-snap1", "build-snap2"],
            "build-packages": ["build-pkg1", "build-pkg2"],
            "build-environment": [{"ENV1": "on"}, {"ENV2": "off"}],
            "build-attributes": ["attr1", "attr2"],
            "organize": {"src1": "dest1", "src2": "dest2"},
            "stage": ["-usr/docs"],
            "prime": ["*"],
            "override-pull": "override-pull",
            "override-build": "override-build",
            "override-stage": "override-stage",
            "override-prime": "override-prime",
        }

        data_copy = deepcopy(data)

        spec = PartSpec.unmarshal(data)
        assert data == data_copy

        new_data = spec.marshal()
        assert new_data == data_copy

    def test_unmarshal_not_dict(self):
        with pytest.raises(TypeError) as raised:
            PartSpec.unmarshal(False)  # type: ignore
        assert str(raised.value) == "part data is not a dictionary"


class TestPartData:
    """Test basic part creation and representation."""

    def test_part_dirs(self, new_dir):
        p = Part("foo", {"plugin": "nil"})
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
        assert p.stage_dir == new_dir / "stage"
        assert p.prime_dir == new_dir / "prime"

    def test_part_work_dir(self, new_dir):
        p = Part("foo", {}, project_dirs=ProjectDirs(work_dir="foobar"))
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
        assert p.stage_dir == new_dir / "foobar/stage"
        assert p.prime_dir == new_dir / "foobar/prime"

    def test_part_subdirs(self, new_dir):
        p = Part("foo", {"source-subdir": "foobar"})
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
        "tc_spec,tc_result",
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
        "tc_spec,tc_result",
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
        "tc_spec,tc_result",
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
        "tc_spec,tc_result",
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
        "tc_step,tc_content",
        [
            (Step.PULL, "pull"),
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
            },
        )
        assert p.spec.get_scriptlet(tc_step) == tc_content

    @pytest.mark.parametrize(
        "step",
        [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME],
    )
    def test_part_get_scriptlet_none(self, step):
        p = Part("foo", {})
        assert p.spec.get_scriptlet(step) is None


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
            "'a': extra fields not permitted\n'b': extra fields not permitted"
        )

    def test_part_spec_not_dict(self):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", False)  # type: ignore
        assert raised.value.part_name == "foo"
        assert raised.value.message == "part data is not a dictionary"

    def test_part_unmarshal_type_error(self):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", {"plugin": []})
        assert raised.value.part_name == "foo"
        assert raised.value.message == "'plugin': str type expected"

    @pytest.mark.parametrize("fileset", ["stage", "prime"])
    def test_relative_path_validation(self, fileset):
        with pytest.raises(errors.PartSpecificationError) as raised:
            Part("foo", {fileset: ["bar", "/baz", ""]})
        assert raised.value.part_name == "foo"
        assert raised.value.message == (
            f"{fileset!r},1: '/baz' must be a relative path (cannot start with '/')\n"
            f"{fileset!r},2: path cannot be empty"
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

        x = parts.part_dependencies("foo", part_list=[p1, p2, p3, p4])
        assert x == {p2, p3}

        x = parts.part_dependencies("foo", part_list=[p1, p2, p3, p4], recursive=True)
        assert x == {p2, p3, p4}

        with pytest.raises(errors.InvalidPartName) as raised:
            parts.part_dependencies("invalid", part_list=[p1, p2, p3, p4])
        assert raised.value.part_name == "invalid"
