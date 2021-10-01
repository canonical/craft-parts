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

import textwrap
from pathlib import Path
from typing import Dict, List, Set

import pytest

from craft_parts import plugins
from craft_parts.executor import environment
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


class FooPlugin(plugins.Plugin):
    """A test plugin."""

    properties_class = plugins.PluginProperties

    def get_build_snaps(self) -> Set[str]:
        return set()

    def get_build_packages(self) -> Set[str]:
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        return {"PLUGIN_ENVVAR": "from_plugin"}

    def get_build_commands(self) -> List[str]:
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


def test_generate_part_environment_build(new_dir):
    p1 = Part("p1", {"build-environment": [{"PART_ENVVAR": "from_part"}]})
    info = ProjectInfo(arch="aarch64", application_name="xyz", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.BUILD)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_part_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        """\
        #!/bin/sh
        set -e
        # Environment
        ## Part Environment
        export XYZ_ARCH_TRIPLET="aarch64-linux-gnu"
        export XYZ_TARGET_ARCH="arm64"
        export XYZ_PARALLEL_BUILD_COUNT="1"
        export XYZ_PART_NAME="p1"
        export XYZ_PART_SRC="{0}/parts/p1/src"
        export XYZ_PART_BUILD="{0}/parts/p1/build"
        export XYZ_PART_BUILD_WORK="{0}/parts/p1/build"
        export XYZ_PART_INSTALL="{0}/parts/p1/install"
        export XYZ_OVERLAY="{0}/overlay/overlay"
        export XYZ_STAGE="{0}/stage"
        export XYZ_PRIME="{0}/prime"
        export PATH="{0}/parts/p1/install/usr/sbin:{0}/parts/p1/install/usr/bin:{0}/parts/p1/install/sbin:{0}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export LDFLAGS="-L{0}/stage/lib -L{0}/stage/usr/lib -L{0}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{0}/stage/usr/share/pkgconfig"
        ## Plugin Environment
        export PLUGIN_ENVVAR="from_plugin"
        ## User Environment
        export PART_ENVVAR="from_part"
        """.format(
            new_dir
        )
    )


def test_generate_part_environment_no_build(new_dir):
    p1 = Part("p1", {"build-environment": [{"PART_ENVVAR": "from_part"}]})
    info = ProjectInfo(arch="aarch64", application_name="xyz", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.STAGE)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_part_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        """\
        #!/bin/sh
        set -e
        # Environment
        ## Part Environment
        export XYZ_ARCH_TRIPLET="aarch64-linux-gnu"
        export XYZ_TARGET_ARCH="arm64"
        export XYZ_PARALLEL_BUILD_COUNT="1"
        export XYZ_PART_NAME="p1"
        export XYZ_PART_SRC="{0}/parts/p1/src"
        export XYZ_PART_BUILD="{0}/parts/p1/build"
        export XYZ_PART_BUILD_WORK="{0}/parts/p1/build"
        export XYZ_PART_INSTALL="{0}/parts/p1/install"
        export XYZ_OVERLAY="{0}/overlay/overlay"
        export XYZ_STAGE="{0}/stage"
        export XYZ_PRIME="{0}/prime"
        export PATH="{0}/parts/p1/install/usr/sbin:{0}/parts/p1/install/usr/bin:{0}/parts/p1/install/sbin:{0}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export LDFLAGS="-L{0}/stage/lib -L{0}/stage/usr/lib -L{0}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{0}/stage/usr/share/pkgconfig"
        ## Plugin Environment
        ## User Environment
        export PART_ENVVAR="from_part"
        """.format(
            new_dir
        )
    )


def test_generate_part_environment_no_user_env(new_dir):
    p1 = Part("p1", {})
    info = ProjectInfo(arch="aarch64", application_name="xyz", cache_dir=new_dir)
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=Step.BUILD)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)

    env = environment.generate_part_environment(
        part=p1, plugin=plugin, step_info=step_info
    )

    assert env == textwrap.dedent(
        """\
        #!/bin/sh
        set -e
        # Environment
        ## Part Environment
        export XYZ_ARCH_TRIPLET="aarch64-linux-gnu"
        export XYZ_TARGET_ARCH="arm64"
        export XYZ_PARALLEL_BUILD_COUNT="1"
        export XYZ_PART_NAME="p1"
        export XYZ_PART_SRC="{0}/parts/p1/src"
        export XYZ_PART_BUILD="{0}/parts/p1/build"
        export XYZ_PART_BUILD_WORK="{0}/parts/p1/build"
        export XYZ_PART_INSTALL="{0}/parts/p1/install"
        export XYZ_OVERLAY="{0}/overlay/overlay"
        export XYZ_STAGE="{0}/stage"
        export XYZ_PRIME="{0}/prime"
        export PATH="{0}/parts/p1/install/usr/sbin:{0}/parts/p1/install/usr/bin:{0}/parts/p1/install/sbin:{0}/parts/p1/install/bin:$PATH"
        export CPPFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export CXXFLAGS="-isystem {0}/parts/p1/install/usr/include"
        export LDFLAGS="-L{0}/stage/lib -L{0}/stage/usr/lib -L{0}/stage/lib/aarch64-linux-gnu"
        export PKG_CONFIG_PATH="{0}/stage/usr/share/pkgconfig"
        ## Plugin Environment
        export PLUGIN_ENVVAR="from_plugin"
        ## User Environment
        """.format(
            new_dir
        )
    )
