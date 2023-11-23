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

import os
import textwrap

import craft_parts
import pytest
import yaml
from craft_parts import Action, ProjectInfo, Step, StepInfo, callbacks


@pytest.fixture(autouse=True)
def setup_feature(enable_overlay_feature):
    return


def setup_function():
    callbacks.unregister_all()


def teardown_module():
    callbacks.unregister_all()


@pytest.fixture(autouse=True)
def mock_mount_unmount(mocker):
    mocker.patch("craft_parts.utils.os_utils.mount")
    mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
    mocker.patch("craft_parts.utils.os_utils.umount")


@pytest.fixture(autouse=True)
def mock_prerequisites_for_overlay(mocker):
    mocker.patch("craft_parts.lifecycle_manager._ensure_overlay_supported")
    mocker.patch("craft_parts.overlays.OverlayManager.refresh_packages_list")


def _prologue_callback(info: ProjectInfo) -> None:
    info.global_environment["TEST_GLOBAL"] = "prologue"


def _step_callback(info: StepInfo) -> bool:
    info.step_environment.update(
        {
            "TEST_OVERRIDE": "foo",
            "TEST_STEP": str(info.step),
        }
    )
    return True


_parts_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        override-pull: env | egrep "^(TEST|CRAFT)_" | sort
        overlay-script: env | egrep "^(TEST|CRAFT)_" | sort
        override-build: env | egrep "^(TEST|CRAFT)_" | sort
        override-stage: env | egrep "^(TEST|CRAFT)_" | sort
        override-prime: env | egrep "^(TEST|CRAFT)_" | sort
        build-environment:
          - TEST_OVERRIDE: bar
    """
)


@pytest.mark.parametrize("step", list(Step))
def test_step_callback(new_dir, mocker, capfd, step):
    mocker.patch("platform.machine", return_value="aarch64")

    callbacks.register_pre_step(_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_step_callback",
        cache_dir=new_dir,
        work_dir=new_dir,
        base_layer_dir=new_dir,
        base_layer_hash=b"hash",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step))

    out, _err = capfd.readouterr()
    assert out == (
        textwrap.dedent(
            f"""\
            CRAFT_ARCH_BUILD_FOR=arm64
            CRAFT_ARCH_BUILD_ON=arm64
            CRAFT_ARCH_TRIPLET=aarch64-linux-gnu
            CRAFT_ARCH_TRIPLET_BUILD_FOR=aarch64-linux-gnu
            CRAFT_ARCH_TRIPLET_BUILD_ON=aarch64-linux-gnu
            CRAFT_OVERLAY={new_dir}/overlay/overlay
            CRAFT_PARALLEL_BUILD_COUNT=1
            CRAFT_PART_BUILD={new_dir}/parts/foo/build
            CRAFT_PART_BUILD_WORK={new_dir}/parts/foo/build
            CRAFT_PART_INSTALL={new_dir}/parts/foo/install
            CRAFT_PART_NAME=foo
            CRAFT_PART_SRC={new_dir}/parts/foo/src
            CRAFT_PART_SRC_WORK={new_dir}/parts/foo/src
            CRAFT_PRIME={new_dir}/prime
            CRAFT_PROJECT_DIR={os.getcwd()}
            CRAFT_STAGE={new_dir}/stage
            CRAFT_STEP_NAME={Step(step).name}
            CRAFT_TARGET_ARCH=arm64
            TEST_OVERRIDE=bar
            TEST_STEP={step!s}
            """
        )
    )


def test_prologue_callback(new_dir, capfd, mocker):
    mocker.patch("platform.machine", return_value="aarch64")

    callbacks.register_prologue(_prologue_callback)

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_prologue_callback",
        cache_dir=new_dir,
        work_dir=new_dir,
        base_layer_dir=new_dir,
        base_layer_hash=b"hash",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, _err = capfd.readouterr()
    assert out == (
        textwrap.dedent(
            f"""\
            CRAFT_ARCH_BUILD_FOR=arm64
            CRAFT_ARCH_BUILD_ON=arm64
            CRAFT_ARCH_TRIPLET=aarch64-linux-gnu
            CRAFT_ARCH_TRIPLET_BUILD_FOR=aarch64-linux-gnu
            CRAFT_ARCH_TRIPLET_BUILD_ON=aarch64-linux-gnu
            CRAFT_OVERLAY={new_dir}/overlay/overlay
            CRAFT_PARALLEL_BUILD_COUNT=1
            CRAFT_PART_BUILD={new_dir}/parts/foo/build
            CRAFT_PART_BUILD_WORK={new_dir}/parts/foo/build
            CRAFT_PART_INSTALL={new_dir}/parts/foo/install
            CRAFT_PART_NAME=foo
            CRAFT_PART_SRC={new_dir}/parts/foo/src
            CRAFT_PART_SRC_WORK={new_dir}/parts/foo/src
            CRAFT_PRIME={new_dir}/prime
            CRAFT_PROJECT_DIR={os.getcwd()}
            CRAFT_STAGE={new_dir}/stage
            CRAFT_STEP_NAME=PULL
            CRAFT_TARGET_ARCH=arm64
            TEST_GLOBAL=prologue
            TEST_OVERRIDE=bar
            """
        )
    )


def test_expand_environment(new_dir, mocker):
    mocker.patch("platform.machine", return_value="aarch64")
    parts_yaml = """\
        parts:
          foo:
            plugin: nil
            override-build: |
              touch $CRAFT_PART_INSTALL/bar
            organize:
              bar: usr/$CRAFT_ARCH_TRIPLET/bar
        """

    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_expansion",
        cache_dir=new_dir,
        work_dir=new_dir,
    )

    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert (lf.project_info.prime_dir / "usr/aarch64-linux-gnu/bar").is_file()


def test_expand_environment_order(new_dir, mocker):
    """The largest replacements should occur first.

    $CRAFT_ARCH_TRIPLET_BUILD_{ON|FOR} should be replaced before $CRAFT_ARCH_TRIPLET
    """
    mocker.patch("platform.machine", return_value="aarch64")
    parts_yaml = """\
        parts:
          foo:
            plugin: nil
            override-build: |
                cat << EOF >> $CRAFT_PART_INSTALL/part-variables.txt
                CRAFT_ARCH_TRIPLET_1: $CRAFT_ARCH_TRIPLET
                CRAFT_ARCH_TRIPLET_2: ${CRAFT_ARCH_TRIPLET}
                CRAFT_ARCH_TRIPLET_BUILD_FOR_1: $CRAFT_ARCH_TRIPLET_BUILD_FOR
                CRAFT_ARCH_TRIPLET_BUILD_FOR_2: ${CRAFT_ARCH_TRIPLET_BUILD_FOR}
                CRAFT_ARCH_TRIPLET_BUILD_ON_1: $CRAFT_ARCH_TRIPLET_BUILD_ON
                CRAFT_ARCH_TRIPLET_BUILD_ON_1: ${CRAFT_ARCH_TRIPLET_BUILD_ON}
                EOF

        """

    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_expansion",
        cache_dir=new_dir,
        work_dir=new_dir,
    )

    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    with open(lf.project_info.prime_dir / "part-variables.txt") as file:
        data = file.read()

    assert data == textwrap.dedent(
        """\
        CRAFT_ARCH_TRIPLET_1: aarch64-linux-gnu
        CRAFT_ARCH_TRIPLET_2: aarch64-linux-gnu
        CRAFT_ARCH_TRIPLET_BUILD_FOR_1: aarch64-linux-gnu
        CRAFT_ARCH_TRIPLET_BUILD_FOR_2: aarch64-linux-gnu
        CRAFT_ARCH_TRIPLET_BUILD_ON_1: aarch64-linux-gnu
        CRAFT_ARCH_TRIPLET_BUILD_ON_1: aarch64-linux-gnu
        """
    )
