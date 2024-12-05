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

from pathlib import Path

import pytest
from craft_parts import errors, infos
from craft_parts.dirs import ProjectDirs
from craft_parts.infos import PartInfo, ProjectInfo, ProjectVar, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step

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
        "project_vars": {"a": ProjectVar(value="b")},
    }
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
        "project_vars": {"a": ProjectVar(value="b")},
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


def test_project_info_set_project_var():
    info = ProjectInfo(
        application_name="test", cache_dir=Path(), project_vars={"var": "foo"}
    )

    info.set_project_var("var", "bar")
    assert info.get_project_var("var", raw_read=True) == "bar"


def test_project_info_set_project_raw_write():
    info = ProjectInfo(
        application_name="test", cache_dir=Path(), project_vars={"var": "foo"}
    )

    info.set_project_var("var", "bar")
    info.set_project_var("var", "bar", raw_write=True)
    with pytest.raises(RuntimeError) as raised:
        info.set_project_var("var", "bar")

    assert str(raised.value) == "variable 'var' can be set only once"


def test_project_info_set_project_var_bad_name():
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(ValueError) as raised:  # noqa: PT011
        info.set_project_var("bad-name", "foo")
    assert str(raised.value) == "'bad-name' is not a valid variable name"


def test_project_info_set_project_var_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="part1",
        project_vars={"var": "foo"},
    )

    info.set_project_var("var", "bar", part_name="part1")
    assert info.get_project_var("var", raw_read=True) == "bar"


def test_project_info_set_project_var_no_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars={"var": "foo"},
    )

    with pytest.raises(RuntimeError) as raised:
        info.set_project_var("var", "bar", part_name="part2")

    assert str(raised.value) == (
        "variable 'var' can only be set in a part that adopts external metadata"
    )


def test_project_info_set_project_var_other_part_name():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="part1",
        project_vars={"var": "foo"},
    )

    with pytest.raises(RuntimeError) as raised:
        info.set_project_var("var", "bar", part_name="part2")

    assert str(raised.value) == "variable 'var' can only be set in part 'part1'"


def test_project_info_set_project_var_no_part_name_raw():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars={"var": "foo"},
    )

    info.set_project_var("var", "bar", part_name="part2", raw_write=True)
    assert info.get_project_var("var", raw_read=True) == "bar"


def test_project_info_set_project_var_other_part_name_raw():
    info = ProjectInfo(
        application_name="test",
        cache_dir=Path(),
        project_vars_part_name="part1",
        project_vars={"var": "foo"},
    )

    info.set_project_var("var", "bar", part_name="part2", raw_write=True)
    assert info.get_project_var("var", raw_read=True) == "bar"


def test_project_info_set_invalid_project_vars():
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(ValueError) as raised:  # noqa: PT011
        info.set_project_var("var", "bar")
    assert str(raised.value) == "'var' not in project variables"


def test_project_info_get_project_var_bad_name():
    info = ProjectInfo(application_name="test", cache_dir=Path())

    with pytest.raises(ValueError) as raised:  # noqa: PT011
        info.get_project_var("bad-name")
    assert str(raised.value) == "'bad-name' is not a valid variable name"


def test_project_info_default():
    info = ProjectInfo(application_name="test", cache_dir=Path())
    assert info.parallel_build_count == 1


def test_project_info_cache_dir_resolving():
    info = ProjectInfo(application_name="test", cache_dir=Path("~/x/../y/."))
    assert info.cache_dir == Path.home() / "y"


def test_project_info_get_project_var():
    info = ProjectInfo(
        application_name="test", cache_dir=Path(), project_vars={"var": "foo"}
    )

    info.set_project_var("var", "bar")
    assert info.get_project_var("var", raw_read=True) == "bar"
    with pytest.raises(RuntimeError) as raised:
        info.get_project_var("var")

    assert str(raised.value) == (
        "cannot consume variable 'var' during lifecycle execution"
    )


def test_project_info_consume_project_var_during_lifecycle():
    info = ProjectInfo(
        application_name="test", cache_dir=Path(), project_vars={"var": "foo"}
    )

    info.set_project_var("var", "bar")
    assert info.get_project_var("var", raw_read=True) == "bar"
    with pytest.raises(RuntimeError) as raised:
        info.get_project_var("var")

    assert str(raised.value) == (
        "cannot consume variable 'var' during lifecycle execution"
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

    with pytest.raises(ValueError) as raised:  # noqa: PT011
        x.set_project_var("var", "bar")
    assert str(raised.value) == "'var' not in project variables"


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

    with pytest.raises(ValueError) as raised:  # noqa: PT011
        x.set_project_var("var", "bar")
    assert str(raised.value) == "'var' not in project variables"


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
