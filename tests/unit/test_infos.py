# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2022 Canonical Ltd.
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

import logging
import re
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from unittest.mock import call

import pytest
from craft_parts import errors, infos
from craft_parts.dirs import ProjectDirs
from craft_parts.infos import (
    PartInfo,
    ProjectInfo,
    ProjectVar,
    ProjectVarInfo,
    StepInfo,
)
from craft_parts.parts import Part
from craft_parts.steps import Step

pytestmark = [
    pytest.mark.filterwarnings(
        "ignore:Using deprecated API to define project variables."
    ),
    pytest.mark.filterwarnings(
        "ignore:'ProjectInfo.project_vars_part_name' is deprecated."
    ),
]


_MOCK_NATIVE_ARCH = "arm64"

LINUX_ARCHS = [
    ("aarch64", "arm64", "aarch64-linux-gnu", False),
    ("armv7l", "armhf", "arm-linux-gnueabihf", True),
    ("i686", "i386", "i386-linux-gnu", True),
    ("ppc", "powerpc", "powerpc-linux-gnu", True),
    ("ppc64le", "ppc64el", "powerpc64le-linux-gnu", True),
    ("riscv64", "riscv64", "riscv64-linux-gnu", True),
    ("s390x", "s390x", "s390x-linux-gnu", True),
    ("x86_64", "amd64", "x86_64-linux-gnu", True),
]


@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("craft_parts.infos.logger", spec=logging.Logger)


@pytest.mark.parametrize(
    ("tc_arch", "tc_target_arch", "tc_triplet", "tc_cross"), LINUX_ARCHS
)
def test_project_info(mocker, new_dir, tc_arch, tc_target_arch, tc_triplet, tc_cross):
    mocker.patch("platform.machine", return_value=_MOCK_NATIVE_ARCH)

    x = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        arch=tc_target_arch,
        parallel_build_count=16,
        project_vars_part_name="adopt",
        project_vars={"a": "b"},
        project_name="project",
        custom1="foobar",
        custom2=[1, 2],
    )

    assert x.application_name == "test"
    assert x.cache_dir == new_dir
    assert x.arch_triplet == tc_triplet
    assert x.is_cross_compiling == tc_cross
    assert x.parallel_build_count == 16
    assert x.target_arch == tc_target_arch
    assert x.project_name == "project"
    assert x.project_options == {
        "application_name": "test",
        "arch_triplet": tc_triplet,
        "target_arch": tc_target_arch,
        "project_vars_part_name": "adopt",
        "project_vars": ProjectVarInfo.unmarshal(
            {"a": {"value": "b", "part-name": "adopt"}}
        ),
    }
    assert x.project_vars == ProjectVarInfo.unmarshal(
        {"a": ProjectVar(value="b", part_name="adopt").marshal()}
    )
    assert x.project_vars_part_name == "adopt"
    assert x.global_environment == {}

    assert x.parts_dir == new_dir / "parts"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"


@pytest.mark.parametrize(
    ("machine_arch", "expected_arch"),
    [
        ("ARM64", "arm64"),
        ("armv7hl", "armhf"),
        ("i386", "i386"),
        ("AMD64", "amd64"),
        ("x64", "amd64"),
        ("aarch64", "arm64"),
    ],
)
@pytest.mark.parametrize(
    ("tc_arch", "tc_target_arch", "tc_triplet", "unused_tc_cross"), LINUX_ARCHS
)
def test_project_info_translated_arch(  # pylint: disable=too-many-arguments
    mocker,
    new_dir,
    tc_arch,
    tc_target_arch,
    tc_triplet,
    unused_tc_cross,
    machine_arch,
    expected_arch,
):
    mocker.patch("platform.machine", return_value=machine_arch)

    x = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        arch=tc_target_arch,
        parallel_build_count=16,
        project_vars_part_name="adopt",
        project_vars={"a": "b"},
        project_name="project",
        custom1="foobar",
        custom2=[1, 2],
    )

    assert x.application_name == "test"
    assert x.cache_dir == new_dir
    assert x.arch_triplet == tc_triplet
    assert x.is_cross_compiling == (expected_arch != tc_target_arch)
    assert x.parallel_build_count == 16
    assert x.target_arch == tc_target_arch
    assert x.project_name == "project"
    assert x.project_options == {
        "application_name": "test",
        "arch_triplet": tc_triplet,
        "target_arch": tc_target_arch,
        "project_vars_part_name": "adopt",
        "project_vars": ProjectVarInfo.unmarshal(
            {"a": ProjectVar(value="b", part_name="adopt").marshal()}
        ),
    }
    assert x.global_environment == {}

    assert x.parts_dir == new_dir / "parts"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"


@pytest.mark.parametrize("arch", ["Z80", "invalid-arch"])
def test_project_info_invalid_arch(arch):
    with pytest.raises(errors.InvalidArchitecture):
        ProjectInfo(
            application_name="test",
            cache_dir=Path(),
            arch=arch,
        )


def test_project_info_work_dir(new_dir, partitions):
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_dirs=ProjectDirs(work_dir="work_dir", partitions=partitions),
    )

    assert info.project_dir == new_dir
    assert info.parts_dir == new_dir / "work_dir/parts"
    assert info.stage_dir == new_dir / "work_dir/stage"
    assert info.prime_dir == new_dir / "work_dir/prime"


def test_project_info_custom_args():
    info = ProjectInfo(
        application_name="test", cache_dir=Path(), custom1="foobar", custom2=[1, 2]
    )

    assert info.custom_args == ["custom1", "custom2"]
    assert info.custom1 == "foobar"
    assert info.custom2 == [1, 2]


def test_project_info_invalid_custom_args():
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(AttributeError) as raised:
        print(info.custom1)
    assert str(raised.value) == "'ProjectInfo' has no attribute 'custom1'"


@pytest.mark.parametrize(
    ("kwargs", "project_vars", "expectation"),
    [
        pytest.param(
            {
                "project_vars": ProjectVarInfo.unmarshal(
                    {"var": ProjectVar(value="foo").marshal()}
                ),
            },
            ProjectVarInfo.unmarshal({"var": ProjectVar(value="foo").marshal()}),
            does_not_raise(),
            id="no part name",
        ),
        pytest.param(
            {
                "project_vars": ProjectVarInfo.unmarshal(
                    {"var": ProjectVar(value="foo", part_name="part1").marshal()}
                ),
            },
            ProjectVarInfo.unmarshal(
                {"var": ProjectVar(value="foo", part_name="part1").marshal()}
            ),
            does_not_raise(),
            id="with part name",
        ),
        pytest.param(
            {"project_vars": {"var": "foo"}},
            ProjectVarInfo.unmarshal({"var": ProjectVar(value="foo").marshal()}),
            does_not_raise(),
            id="deprecated api with no part name",
        ),
        pytest.param(
            {"project_vars": {"var": "foo"}, "project_vars_part_name": "part1"},
            ProjectVarInfo.unmarshal(
                {"var": ProjectVar(value="foo", part_name="part1").marshal()}
            ),
            does_not_raise(),
            id="deprecated api with part name",
        ),
        pytest.param(
            {
                "project_vars": ProjectVarInfo.unmarshal(
                    {"var": ProjectVar(value="foo").marshal()}
                ),
                "project_vars_part_name": "part1",
            },
            None,
            pytest.raises(
                RuntimeError,
                match="Cannot handle 'project_vars' of type ProjectVarInfo and 'project_vars_part_name'",
            ),
            id="error for mixed APIs",
        ),
    ],
)
def test_project_info_init(kwargs, project_vars, expectation):
    """Initialize project variables with the current and deprecated APIs."""
    with expectation:
        assert (
            ProjectInfo(
                application_name="test", cache_dir=Path(), **kwargs
            ).project_options["project_vars"]
            == project_vars
        )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var(path):
    """Set a project variable."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz")

    assert info.get_project_var(path, raw_read=True) == "baz"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_raw_write(path):
    """Force-set a project variable with 'raw-write'."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz")
    info.set_project_var(path, "baz", raw_write=True)

    with pytest.raises(RuntimeError) as raised:
        info.set_project_var(path, "bar")

    assert str(raised.value) == f"variable {path!r} can be set only once"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("", id="empty"),
        pytest.param("bad-name", id="hyphen"),
        pytest.param("bad.bad-name", id="nested hyphen"),
        pytest.param(".badname", id="starts with dot"),
        pytest.param("badname.", id="ends with dot"),
        pytest.param("bad..name", id="multiple dots"),
        pytest.param("..badname", id="starts with multiple dots"),
        pytest.param("badname..", id="ends with multiple dots"),
        pytest.param("0badname", id="starts with digit"),
        pytest.param("bad.0badname", id="nested starts with digit"),
        pytest.param(".", id="dot"),
        pytest.param("..", id="dotdot"),
        pytest.param("...", id="et cetera"),
    ],
)
def test_project_info_set_project_var_bad_name(path):
    """Error on invalid project variable names."""
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(ValueError, match=f"{path!r} is not a valid variable name"):
        info.set_project_var(path, "foo")


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var_part_name(path):
    """Set a project variable from its part."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo", part_name="part1").marshal(),
                "b": {
                    "c": ProjectVar(value="bar", part_name="part1").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz", part_name="part1")
    assert info.get_project_var(path, raw_read=True) == "baz"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var_no_part_name(path):
    """Error when setting a variable that has no part, from a part."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    with pytest.raises(RuntimeError) as raised:
        info.set_project_var(path, "baz", part_name="part2")

    assert str(raised.value) == (
        f"variable {path!r} can only be set in a part that adopts external metadata"
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var_other_part_name(path):
    """Error when setting a variable from the wrong part."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo", part_name="part1").marshal(),
                "b": {
                    "c": ProjectVar(value="bar", part_name="part1").marshal(),
                },
            }
        ),
    )

    with pytest.raises(RuntimeError) as raised:
        info.set_project_var(path, "bar", part_name="part2")

    assert str(raised.value) == f"variable {path!r} can only be set in part 'part1'"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var_no_part_name_raw(path):
    """Force-set a project variable with no part, from a part."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz", part_name="part2", raw_write=True)
    assert info.get_project_var(path, raw_read=True) == "baz"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_set_project_var_other_part_name_raw(path):
    """Force-set a project variable with a part, from a different part."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo", part_name="part1").marshal(),
                "b": {
                    "c": ProjectVar(value="bar", part_name="part1").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz", part_name="part2", raw_write=True)

    assert info.get_project_var(path, raw_read=True) == "baz"


def test_project_info_set_invalid_project_vars():
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(ValueError, match="^'var' not in project variables$"):
        info.set_project_var("var", "bar")


def test_project_info_default():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    assert info.parallel_build_count == 1
    assert not info.usrmerged_by_default


def test_project_info_cache_dir_resolving():
    info = ProjectInfo(application_name="test", cache_dir=Path("~/x/../y/."))
    assert info.cache_dir == Path.home() / "y"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_get_project_var(path):
    """Get a project variable with raw_read."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz")
    value = info.get_project_var(path, raw_read=True)

    assert value == "baz"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("a", id="top level"),
        pytest.param("b.c", id="nested"),
    ],
)
def test_project_info_get_project_var_during_lifecycle(path):
    """Error when getting a project var before the lifecycle completes."""
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars=ProjectVarInfo.unmarshal(
            {
                "a": ProjectVar(value="foo").marshal(),
                "b": {
                    "c": ProjectVar(value="bar").marshal(),
                },
            }
        ),
    )

    info.set_project_var(path, "baz")
    with pytest.raises(RuntimeError) as raised:
        info.get_project_var(path)

    assert str(raised.value) == (
        f"cannot consume variable {path!r} during lifecycle execution"
    )


def test_invalid_arch():
    with pytest.raises(errors.InvalidArchitecture) as raised:
        ProjectInfo(application_name="test", cache_dir=Path(), arch="invalid")
    assert raised.value.arch_name == "invalid"


def test_part_info(new_dir):
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_name="project",
        custom1="foobar",
        custom2=[1, 2],
    )
    part = Part("foo", {"build-attributes": ["bar"]})
    x = PartInfo(project_info=info, part=part)

    assert x.application_name == "test"
    assert x.cache_dir == new_dir
    assert x.project_name == "project"
    assert x.parallel_build_count == 1
    assert x.global_environment == {}

    assert x.part_name == "foo"
    assert x.part_src_dir == new_dir / "parts/foo/src"
    assert x.part_src_subdir == new_dir / "parts/foo/src"
    assert x.part_build_dir == new_dir / "parts/foo/build"
    assert x.part_build_subdir == new_dir / "parts/foo/build"
    assert x.part_install_dir == new_dir / "parts/foo/install"
    assert x.part_state_dir == new_dir / "parts/foo/state"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"
    assert x.build_attributes == ["bar"]

    assert x.custom_args == ["custom1", "custom2"]
    assert x.custom1 == "foobar"
    assert x.custom2 == [1, 2]


def test_part_info_invalid_custom_args():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("foo", {})
    x = PartInfo(project_info=info, part=part)

    with pytest.raises(AttributeError) as raised:
        print(x.custom1)
    assert str(raised.value) == "'PartInfo' has no attribute 'custom1'"


def test_part_info_set_project_var():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"


def test_part_info_set_project_var_raw_write():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    x.set_project_var("var", "bar")
    x.set_project_var("var", "bar", raw_write=True)
    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == "variable 'var' can be set only once"


def test_part_info_set_project_var_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"


def test_part_info_set_project_var_no_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == (
        "variable 'var' can only be set in a part that adopts external metadata"
    )


def test_part_info_set_project_var_other_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p2",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == "variable 'var' can only be set in part 'p2'"


def test_part_info_set_invalid_project_vars():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    with pytest.raises(ValueError, match="^'var' not in project variables$"):
        x.set_project_var("var", "bar")


def test_part_info_get_project_var():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    x = PartInfo(project_info=info, part=part)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"
    with pytest.raises(RuntimeError) as raised:
        x.get_project_var("var")

    assert str(raised.value) == (
        "cannot consume variable 'var' during lifecycle execution"
    )


def test_part_info_part_dependencies():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("foo", {"after": ["part1", "part2"]})
    x = PartInfo(project_info=info, part=part)
    assert x.part_dependencies == ["part1", "part2"]


@pytest.mark.parametrize("plugin", ["nil", "dump", "make"])
def test_part_info_plugin_name(plugin):
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("foo", {"plugin": plugin})
    x = PartInfo(project_info=info, part=part)
    assert x.plugin_name == plugin


def test_step_info(new_dir):
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_name="project",
        custom1="foobar",
        custom2=[1, 2],
    )
    part = Part("foo", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.BUILD)

    assert x.application_name == "test"
    assert x.cache_dir == new_dir
    assert x.project_name == "project"
    assert x.parallel_build_count == 1

    assert x.part_name == "foo"
    assert x.part_src_dir == new_dir / "parts/foo/src"
    assert x.part_src_subdir == new_dir / "parts/foo/src"
    assert x.part_build_dir == new_dir / "parts/foo/build"
    assert x.part_build_subdir == new_dir / "parts/foo/build"
    assert x.part_install_dir == new_dir / "parts/foo/install"
    assert x.stage_dir == new_dir / "stage"
    assert x.prime_dir == new_dir / "prime"

    assert x.step == Step.BUILD
    assert x.global_environment == {}
    assert x.step_environment == {}
    assert x.state is None

    assert x.custom_args == ["custom1", "custom2"]
    assert x.custom1 == "foobar"
    assert x.custom2 == [1, 2]


def test_step_info_invalid_custom_args():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("foo", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    with pytest.raises(AttributeError) as raised:
        print(x.custom1)
    assert str(raised.value) == "'StepInfo' has no attribute 'custom1'"


def test_step_info_set_project_var():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"


def test_step_info_set_project_var_raw_write():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    x.set_project_var("var", "bar")
    x.set_project_var("var", "bar", raw_write=True)
    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == "variable 'var' can be set only once"


def test_step_info_set_project_var_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"


def test_step_info_set_project_var_no_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == (
        "variable 'var' can only be set in a part that adopts external metadata"
    )


def test_step_info_set_project_var_other_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p2",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    with pytest.raises(RuntimeError) as raised:
        x.set_project_var("var", "bar")

    assert str(raised.value) == "variable 'var' can only be set in part 'p2'"


def test_step_info_set_invalid_project_vars():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    with pytest.raises(ValueError, match="^'var' not in project variables$"):
        x.set_project_var("var", "bar")


def test_step_info_get_project_var():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="p1",
        project_vars={"var": "foo"},
    )
    part = Part("p1", {})
    part_info = PartInfo(project_info=info, part=part)
    x = StepInfo(part_info=part_info, step=Step.PULL)

    x.set_project_var("var", "bar")
    assert x.get_project_var("var", raw_read=True) == "bar"
    with pytest.raises(RuntimeError) as raised:
        x.get_project_var("var")

    assert str(raised.value) == (
        "cannot consume variable 'var' during lifecycle execution"
    )


@pytest.mark.parametrize(
    ("machine", "translated_machine"),
    [
        ("arm64", "arm64"),
        ("armv7hl", "armhf"),
        ("armv8l", "armhf"),
        ("i386", "i386"),
        ("AMD64", "amd64"),
        ("x64", "amd64"),
        ("aarch64", "arm64"),
        ("invalid-architecture", "invalid-architecture"),
    ],
)
def test_get_host_architecture_returns_valid_arch(
    monkeypatch, machine, translated_machine
):
    monkeypatch.setattr("platform.machine", lambda: machine)

    result = infos._get_host_architecture()

    assert result == translated_machine


class TestProjectVarInfo:
    """Tests for the ProjectVarInfo class."""

    def test_marshal_unmarshal(self):
        """Marshal and unmarshal a ProjectVarInfo."""
        data = {
            "a": {
                "b": {
                    "value": "value1",
                },
                "c": {
                    "d": {
                        "value": "value2",
                        "updated": True,
                    }
                },
            },
            "e": {
                "value": "value3",
                "updated": False,
                "part-name": "part3",
            },
            # coerce an int
            "f": {"value": 1},
            # coerce a float
            "g": {"value": 1.0},
        }

        info = ProjectVarInfo.unmarshal(data)
        new_data = info.marshal()

        assert new_data == {
            "a": {
                "b": ProjectVar(
                    value="value1",
                    updated=False,
                    part_name=None,
                ).marshal(),
                "c": {
                    "d": ProjectVar(
                        value="value2",
                        updated=True,
                        part_name=None,
                    ).marshal(),
                },
            },
            "e": ProjectVar(
                value="value3",
                updated=False,
                part_name="part3",
            ).marshal(),
            "f": ProjectVar(
                value="1",
                updated=False,
                part_name=None,
            ).marshal(),
            "g": ProjectVar(
                value="1.0",
                updated=False,
                part_name=None,
            ).marshal(),
        }

    def test_unmarshal_error(self):
        """Error if unmarshalling invalid data."""
        expected_error = "Project variable info must be a dictionary."

        with pytest.raises(TypeError, match=expected_error):
            ProjectVarInfo.unmarshal("invalid")  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize(
        ("attr", "expected"),
        [
            (
                "value",
                {
                    "a": {
                        "b": "value1",
                        "c": {"d": "value2"},
                    },
                    "e": "value3",
                },
            ),
            (
                "updated",
                {
                    "a": {
                        "b": False,
                        "c": {"d": True},
                    },
                    "e": False,
                },
            ),
            (
                "part_name",
                {
                    "a": {
                        "b": None,
                        "c": {"d": None},
                    },
                    "e": "part3",
                },
            ),
        ],
    )
    def test_marshal_one_attribute(self, attr, expected):
        """Unmarshal one attribute of the project vars."""
        info = ProjectVarInfo.unmarshal(
            {
                "a": {
                    "b": ProjectVar(
                        value="value1",
                    ).marshal(),
                    "c": {
                        "d": ProjectVar(
                            value="value2",
                            updated=True,
                        ).marshal(),
                    },
                },
                "e": ProjectVar(
                    value="value3",
                    updated=False,
                    part_name="part3",
                ).marshal(),
            }
        )

        new_data = info.marshal(attr)

        assert new_data == expected

    def test_has_key(self, mock_logger):
        """Check if a key exists."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )

        assert info.has_key("a", "b")
        assert not info.has_key("a")
        assert not info.has_key("a", "b", "c")
        assert not info.has_key("c")
        # assert logs only for the first `has_key()` call
        assert mock_logger.debug.mock_calls[0:4] == [
            call("Checking if 'a.b' exists."),
            call("Getting value for 'a.b'."),
            call("Got 'value' (updated=False) for 'a.b'."),
            call("'a.b' exists."),
        ]

    @pytest.mark.parametrize(
        ("func", "kwargs"),
        [
            ("has_key", {}),
            ("get", {}),
            ("set", {"value": "baz"}),
        ],
    )
    def test_no_keys_error(self, func, kwargs):
        """Error if no keys are provided."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = "No keys provided."

        with pytest.raises(KeyError, match=expected_error):
            getattr(info, func)(**kwargs)

    def test_values(self):
        """Get the values of a ProjectVarInfo."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )

        values = info.values()

        assert list(values) == list(info.root.values())

    def test_get_and_set(self, mock_logger):
        """Test getting and setting a value from ProjectVarInfo."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )

        info.set("a", "b", value="new-value")
        var = info.get("a", "b")

        assert var == ProjectVar(value="new-value", updated=True)
        assert mock_logger.debug.mock_calls == [
            call("Setting 'a.b' to 'new-value'."),
            call("Set 'a.b' to 'new-value'."),
            call("Getting value for 'a.b'."),
            call("Got 'new-value' (updated=True) for 'a.b'."),
        ]

    def test_get_invalid_path_error(self):
        """Error if an item the path doesn't exist."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to get value for 'a.non-existent': 'non-existent' doesn't exist."
        )

        with pytest.raises(KeyError, match=expected_error):
            info.get("a", "non-existent")

    def test_get_invalid_path_top_level_error(self):
        """Error if the top level item in the path doesn't exist."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to get value for 'foo.bar.baz': 'foo' doesn't exist."
        )

        with pytest.raises(KeyError, match=expected_error):
            info.get("foo", "bar", "baz")

    def test_get_into_project_var_error(self):
        """Error if traversing into a ProjectVar to get a value."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to get value for 'a.b.updated': can't traverse into node at 'b'."
        )

        with pytest.raises(KeyError, match=expected_error):
            # try traversing into a value inside a ProjectVar
            info.get("a", "b", "updated")

    def test_get_not_project_var_error(self):
        """Error if getting an intermediate node instead of an end node (a ProjectVar)."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to get value for 'a': value isn't a ProjectVar."
        )

        with pytest.raises(ValueError, match=expected_error):
            # try getting something besides an end node
            info.get("a")

    def test_set_into_project_var_error(self):
        """Error if traversing into a ProjectVar to set a value."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to set 'a.b.updated' to 'new-value': can't traverse into node at 'b'."
        )

        with pytest.raises(KeyError, match=expected_error):
            # try traversing into a value inside a ProjectVar
            info.set("a", "b", "updated", value="new-value")

    def test_set_not_project_var_error(self):
        """Error if setting an intermediate node instead of an end node (a ProjectVar)."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value").marshal()}}
        )
        expected_error = re.escape(
            "Failed to set 'a' to 'new-value': value isn't a ProjectVar."
        )

        with pytest.raises(ValueError, match=expected_error):
            # try setting a value inside a ProjectVar
            info.set("a", value="new-value")

    def test_set_overwrite(self, mock_logger):
        """Overwrite an item that already exists."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value", updated=True).marshal()}}
        )

        info.set("a", "b", value="new-value", overwrite=True)

        assert mock_logger.debug.mock_calls == [
            call("Setting 'a.b' to 'new-value'."),
            call("Overwriting updated value 'value'."),
            call("Set 'a.b' to 'new-value'."),
        ]

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({}, id="default"),
            pytest.param({"overwrite": False}, id="explicit"),
        ],
    )
    def test_set_overwrite_error(self, kwargs, mock_logger):
        """Error if overwrite is false."""
        info = ProjectVarInfo.unmarshal(
            {"a": {"b": ProjectVar(value="value", updated=True).marshal()}}
        )
        expected_error = re.escape(
            "Failed to set 'a.b' to 'new-value': key 'b' already exists and overwrite is false."
        )

        with pytest.raises(ValueError, match=expected_error):
            info.set("a", "b", value="new-value", **kwargs)

    @pytest.mark.parametrize(
        ("part_name", "expected"),
        [
            pytest.param(
                "part1",
                ProjectVarInfo.unmarshal(
                    {
                        "a": {
                            "b": ProjectVar(value="value1").marshal(),
                        },
                        "c": {
                            "d": ProjectVar(
                                value="value2",
                                updated=True,
                                part_name="part2",
                            ).marshal(),
                        },
                        "e": ProjectVar(
                            value="value3",
                            updated=False,
                            part_name="part3",
                        ).marshal(),
                    },
                ),
                # no values updated because no ProjectVars use part1
                id="update-part1",
            ),
            pytest.param(
                "part2",
                ProjectVarInfo.unmarshal(
                    {
                        "a": {
                            "b": ProjectVar(value="value1").marshal(),
                        },
                        "c": {
                            "d": ProjectVar(
                                # value is updated because updated=True and the part name matches
                                value="updated-value2",
                                updated=True,
                                part_name="part2",
                            ).marshal(),
                        },
                        "e": ProjectVar(
                            value="value3",
                            updated=False,
                            part_name="part3",
                        ).marshal(),
                    },
                ),
                id="update-part2",
            ),
            pytest.param(
                "part3",
                ProjectVarInfo.unmarshal(
                    {
                        "a": {
                            "b": ProjectVar(value="value1").marshal(),
                        },
                        "c": {
                            "d": ProjectVar(
                                value="value2",
                                updated=True,
                                part_name="part2",
                            ).marshal(),
                        },
                        "e": ProjectVar(
                            # value isn't updated because updated=False
                            value="value3",
                            updated=False,
                            part_name="part3",
                        ).marshal(),
                    },
                ),
                id="update-part3",
            ),
        ],
    )
    def test_update_from(self, part_name, expected):
        """Update from another ProjectVarInfo class."""
        info = ProjectVarInfo.unmarshal(
            {
                "a": {
                    "b": ProjectVar(value="value1").marshal(),
                },
                "c": {
                    "d": ProjectVar(
                        value="value2",
                        updated=True,
                        part_name="part2",
                    ).marshal(),
                },
                "e": ProjectVar(
                    value="value3",
                    updated=False,
                    part_name="part3",
                ).marshal(),
            },
        )
        other = ProjectVarInfo.unmarshal(
            {
                "a": {
                    "b": ProjectVar(value="updated-value1").marshal(),
                },
                "c": {
                    "d": ProjectVar(
                        value="updated-value2",
                        updated=True,
                        part_name="part2",
                    ).marshal(),
                },
                "e": ProjectVar(
                    value="updated-value3",
                    updated=False,
                    part_name="part3",
                ).marshal(),
            },
        )

        info.update_from(other, part_name)

        assert info == expected
