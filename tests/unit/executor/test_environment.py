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

import logging
import textwrap
from pathlib import Path

import pytest
from craft_parts import plugins
from craft_parts.dirs import ProjectDirs
from craft_parts.executor import environment
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


class FooPlugin(plugins.Plugin):
    """A test plugin."""

    properties_class = plugins.PluginProperties

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {"PLUGIN_ENVVAR": "from_plugin"}

    def get_build_commands(self) -> list[str]:
        return []


@pytest.fixture(autouse=True)
def directories(new_dir):  # pylint: disable=unused-argument
    info = ProjectInfo(application_name="test", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=Part("p1", {}))

    for directory in [
        "bin",
        "usr/bin",
        "sbin",
        "usr/sbin",
        "usr/local/bin",
        "usr/include",
    ]:
        Path(part_info.part_install_dir / directory).mkdir(parents=True)

    for directory in [
        "lib",
        "lib/aarch64-linux-gnu",
        "usr/lib",
        "usr/local/lib",
        "usr/share/pkgconfig",
    ]:
        Path(part_info.stage_dir / directory).mkdir(parents=True)


# pylint: disable=line-too-long


def test_generate_step_environment_build(new_dir):
    p1 = Part("p1", {"build-environment": [{"PART_ENVVAR": "from_part"}]})
    info = ProjectInfo(
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
    )
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.PULL)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)
    step_info.global_environment["APP_GLOBAL_ENVVAR"] = "from_app"
    step_info.step_environment["APP_STEP_ENVVAR"] = "from_app"

    env = environment.generate_step_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        f"""\
        # Environment
        ## Application environment
        export APP_GLOBAL_ENVVAR="from_app"
        export APP_STEP_ENVVAR="from_app"
        ## Part environment
        export CRAFT_ARCH_TRIPLET="aarch64-linux-gnu"
        export CRAFT_TARGET_ARCH="arm64"
        export CRAFT_ARCH_BUILD_ON="amd64"
        export CRAFT_ARCH_BUILD_FOR="arm64"
        export CRAFT_ARCH_TRIPLET_BUILD_ON="x86_64-linux-gnu"
        export CRAFT_ARCH_TRIPLET_BUILD_FOR="aarch64-linux-gnu"
        export CRAFT_PARALLEL_BUILD_COUNT="1"
        export CRAFT_PROJECT_DIR="{new_dir}"
        export CRAFT_STAGE="{new_dir}/stage"
        export CRAFT_PRIME="{new_dir}/prime"
        export CRAFT_PROJECT_NAME="test-project"
        export CRAFT_PART_NAME="p1"
        export CRAFT_STEP_NAME="PULL"
        export CRAFT_PART_SRC="{new_dir}/parts/p1/src"
        export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"
        export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"
        export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"
        export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"
        export PATH="{new_dir}/parts/p1/install/usr/sbin:{new_dir}/parts/p1/install/usr/bin:{new_dir}/parts/p1/install/sbin:{new_dir}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export LDFLAGS="-L{new_dir}/stage/lib -L{new_dir}/stage/usr/lib -L{new_dir}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{new_dir}/stage/usr/share/pkgconfig"
        ## Plugin environment
        ## User environment
        export PART_ENVVAR="from_part"
        """
    )


def test_generate_step_environment_no_project_name(new_dir):
    p1 = Part("p1", {"build-environment": [{"PART_ENVVAR": "from_part"}]})
    info = ProjectInfo(
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
    )
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.BUILD)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_step_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        f"""\
        # Environment
        ## Application environment
        ## Part environment
        export CRAFT_ARCH_TRIPLET="aarch64-linux-gnu"
        export CRAFT_TARGET_ARCH="arm64"
        export CRAFT_ARCH_BUILD_ON="amd64"
        export CRAFT_ARCH_BUILD_FOR="arm64"
        export CRAFT_ARCH_TRIPLET_BUILD_ON="x86_64-linux-gnu"
        export CRAFT_ARCH_TRIPLET_BUILD_FOR="aarch64-linux-gnu"
        export CRAFT_PARALLEL_BUILD_COUNT="1"
        export CRAFT_PROJECT_DIR="{new_dir}"
        export CRAFT_STAGE="{new_dir}/stage"
        export CRAFT_PRIME="{new_dir}/prime"
        export CRAFT_PART_NAME="p1"
        export CRAFT_STEP_NAME="BUILD"
        export CRAFT_PART_SRC="{new_dir}/parts/p1/src"
        export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"
        export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"
        export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"
        export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"
        export PATH="{new_dir}/parts/p1/install/usr/sbin:{new_dir}/parts/p1/install/usr/bin:{new_dir}/parts/p1/install/sbin:{new_dir}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export LDFLAGS="-L{new_dir}/stage/lib -L{new_dir}/stage/usr/lib -L{new_dir}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{new_dir}/stage/usr/share/pkgconfig"
        ## Plugin environment
        export PLUGIN_ENVVAR="from_plugin"
        ## User environment
        export PART_ENVVAR="from_part"
        """
    )


@pytest.mark.parametrize("step", set(Step) - {Step.BUILD})
def test_generate_step_environment_no_build(new_dir, step):
    p1 = Part("p1", {"build-environment": [{"PART_ENVVAR": "from_part"}]})
    info = ProjectInfo(
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
    )
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=step)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_step_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        f"""\
        # Environment
        ## Application environment
        ## Part environment
        export CRAFT_ARCH_TRIPLET="aarch64-linux-gnu"
        export CRAFT_TARGET_ARCH="arm64"
        export CRAFT_ARCH_BUILD_ON="amd64"
        export CRAFT_ARCH_BUILD_FOR="arm64"
        export CRAFT_ARCH_TRIPLET_BUILD_ON="x86_64-linux-gnu"
        export CRAFT_ARCH_TRIPLET_BUILD_FOR="aarch64-linux-gnu"
        export CRAFT_PARALLEL_BUILD_COUNT="1"
        export CRAFT_PROJECT_DIR="{new_dir}"
        export CRAFT_STAGE="{new_dir}/stage"
        export CRAFT_PRIME="{new_dir}/prime"
        export CRAFT_PROJECT_NAME="test-project"
        export CRAFT_PART_NAME="p1"
        export CRAFT_STEP_NAME="{step.name}"
        export CRAFT_PART_SRC="{new_dir}/parts/p1/src"
        export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"
        export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"
        export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"
        export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"
        export PATH="{new_dir}/parts/p1/install/usr/sbin:{new_dir}/parts/p1/install/usr/bin:{new_dir}/parts/p1/install/sbin:{new_dir}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export LDFLAGS="-L{new_dir}/stage/lib -L{new_dir}/stage/usr/lib -L{new_dir}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{new_dir}/stage/usr/share/pkgconfig"
        ## Plugin environment
        ## User environment
        export PART_ENVVAR="from_part"
        """
    )


def test_generate_step_environment_no_user_env(new_dir):
    p1 = Part("p1", {})
    info = ProjectInfo(
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
    )
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.PRIME)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_step_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        f"""\
        # Environment
        ## Application environment
        ## Part environment
        export CRAFT_ARCH_TRIPLET="aarch64-linux-gnu"
        export CRAFT_TARGET_ARCH="arm64"
        export CRAFT_ARCH_BUILD_ON="amd64"
        export CRAFT_ARCH_BUILD_FOR="arm64"
        export CRAFT_ARCH_TRIPLET_BUILD_ON="x86_64-linux-gnu"
        export CRAFT_ARCH_TRIPLET_BUILD_FOR="aarch64-linux-gnu"
        export CRAFT_PARALLEL_BUILD_COUNT="1"
        export CRAFT_PROJECT_DIR="{new_dir}"
        export CRAFT_STAGE="{new_dir}/stage"
        export CRAFT_PRIME="{new_dir}/prime"
        export CRAFT_PROJECT_NAME="test-project"
        export CRAFT_PART_NAME="p1"
        export CRAFT_STEP_NAME="PRIME"
        export CRAFT_PART_SRC="{new_dir}/parts/p1/src"
        export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"
        export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"
        export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"
        export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"
        export PATH="{new_dir}/parts/p1/install/usr/sbin:{new_dir}/parts/p1/install/usr/bin:{new_dir}/parts/p1/install/sbin:{new_dir}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {new_dir}/parts/p1/install/usr/include"
        export LDFLAGS="-L{new_dir}/stage/lib -L{new_dir}/stage/usr/lib -L{new_dir}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{new_dir}/stage/usr/share/pkgconfig"
        ## Plugin environment
        ## User environment
        """
    )


@pytest.mark.parametrize(
    ("var", "value"),
    [
        ("CRAFT_ARCH_TRIPLET", "aarch64-linux-gnu"),
        ("CRAFT_TARGET_ARCH", "arm64"),
        ("CRAFT_STAGE", "/work/stage"),
        ("CRAFT_PRIME", "/work/prime"),
        ("CRAFT_PROJECT_NAME", "test-project"),
        ("ENVVAR", "from_app"),
    ],
)
def test_expand_variables(new_dir, partitions, var, value):
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work", partitions=partitions),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
    )
    info.global_environment.update({"ENVVAR": "from_app"})

    data = {"foo": f"${var}", "bar": f"${{{var}}}"}
    environment.expand_environment(data, info=info)

    assert data == {
        "foo": value,
        "bar": value,
    }


def test_expand_variables_order(mocker, new_dir, partitions):
    """The largest replacements should occur first.

    $CRAFT_ARCH_TRIPLET_BUILD_{ON|FOR} should be replaced before $CRAFT_ARCH_TRIPLET
    """
    mocker.patch("craft_parts.infos._get_host_architecture", return_value="amd64")
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work", partitions=partitions),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
        partitions=partitions,
    )
    info.global_environment.update({"ENVVAR": "from_app"})
    data = {
        "CRAFT_ARCH_TRIPLET_1": "$CRAFT_ARCH_TRIPLET",
        "CRAFT_ARCH_TRIPLET_2": "${CRAFT_ARCH_TRIPLET}",
        "CRAFT_ARCH_TRIPLET_BUILD_FOR_1": "$CRAFT_ARCH_TRIPLET_BUILD_FOR",
        "CRAFT_ARCH_TRIPLET_BUILD_FOR_2": "${CRAFT_ARCH_TRIPLET_BUILD_FOR}",
        "CRAFT_ARCH_TRIPLET_BUILD_ON_1": "$CRAFT_ARCH_TRIPLET_BUILD_ON",
        "CRAFT_ARCH_TRIPLET_BUILD_ON_2": "${CRAFT_ARCH_TRIPLET_BUILD_ON}",
    }

    environment.expand_environment(data, info=info)

    assert data == {
        "CRAFT_ARCH_TRIPLET_1": "aarch64-linux-gnu",
        "CRAFT_ARCH_TRIPLET_2": "aarch64-linux-gnu",
        "CRAFT_ARCH_TRIPLET_BUILD_FOR_1": "aarch64-linux-gnu",
        "CRAFT_ARCH_TRIPLET_BUILD_FOR_2": "aarch64-linux-gnu",
        "CRAFT_ARCH_TRIPLET_BUILD_ON_1": "x86_64-linux-gnu",
        "CRAFT_ARCH_TRIPLET_BUILD_ON_2": "x86_64-linux-gnu",
    }


def test_expand_variables_skip(new_dir, partitions):
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work", partitions=partitions),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
    )
    info.global_environment.update({"ENVVAR": "from_app"})

    data = {"foo": "$CRAFT_PROJECT_NAME", "bar": "$CRAFT_PROJECT_NAME"}
    environment.expand_environment(data, info=info, skip=["foo"])

    assert data == {
        "foo": "$CRAFT_PROJECT_NAME",  # this key was skipped
        "bar": "test-project",
    }


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("$CRAFT_TARGET_ARCH", "arm64"),
        ("${CRAFT_TARGET_ARCH}", "arm64"),
        ("$CRAFT_ARCH_TRIPLET", "aarch64-linux-gnu"),
        ("${CRAFT_ARCH_TRIPLET}", "aarch64-linux-gnu"),
    ],
)
def test_expand_variables_deprecated(new_dir, name, value, caplog):
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work"),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
    )

    data = {"foo": name}
    varname = name.strip("${}")

    with caplog.at_level(logging.DEBUG):
        environment.expand_environment(data, info=info)
        assert data == {"foo": value}  # the variable is still expanded
        assert f"{varname} is deprecated, use" in caplog.text  # but a warning is issued


@pytest.mark.parametrize(
    "invalid_vars",
    [
        {"CRAFT_DEFAULT_STAGE", "CRAFT_DEFAULT_PRIME"},
    ],
)
def test_get_global_environment(new_dir, partitions, invalid_vars):
    """Test that get_global_environment doesn't include partitions when disabled."""
    info = ProjectInfo(
        project_dirs=ProjectDirs(work_dir="/work", partitions=partitions),
        arch="arm64",
        application_name="xyz",
        cache_dir=new_dir,
        project_name="test-project",
        work_dir="/work",
    )

    actual = environment._get_global_environment(info)
    assert invalid_vars.isdisjoint(actual.keys())
