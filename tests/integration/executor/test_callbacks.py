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
from typing import List

import pytest
import yaml

import craft_parts
from craft_parts import (
    Action,
    ActionType,
    Part,
    ProjectInfo,
    Step,
    StepInfo,
    callbacks,
    errors,
)


def setup_function():
    callbacks.unregister_all()


def teardown_module():
    callbacks.unregister_all()


@pytest.fixture(autouse=True)
def mock_mount_unmount(mocker):
    mocker.patch("craft_parts.utils.os_utils.mount")
    mocker.patch("craft_parts.utils.os_utils.umount")


def _step_callback(info: StepInfo) -> bool:
    print(f"step = {info.step!r}")
    print(f"part_src_dir = {info.part_src_dir}")
    print(f"part_build_dir = {info.part_build_dir}")
    print(f"part_install_dir = {info.part_install_dir}")
    return True


def _exec_callback(info: ProjectInfo, part_list: List[Part]) -> None:
    print(f"application_name = {info.application_name}")
    print(f"parts = {', '.join([x.name for x in part_list])}")


_parts_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        override-pull: echo "step Step.PULL"
        overlay-script: echo "step Step.OVERLAY"
        override-build: echo "step Step.BUILD"
        override-stage: echo "step Step.STAGE"
        override-prime: echo "step Step.PRIME"
    """
)


@pytest.mark.parametrize("step", list(Step))
def test_step_callback(tmpdir, capfd, step):
    callbacks.register_pre_step(_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_step_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step))

    out, err = capfd.readouterr()
    assert not err
    assert out == (
        f"step = {step!r}\n"
        f"part_src_dir = {tmpdir}/parts/foo/src\n"
        f"part_build_dir = {tmpdir}/parts/foo/build\n"
        f"part_install_dir = {tmpdir}/parts/foo/install\n"
        f"step {step!r}\n"
    )


def test_prologue_callback(tmpdir, capfd):
    callbacks.register_prologue(_exec_callback)

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_prologue_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == (
        "application_name = test_prologue_callback\n" "parts = foo\n" "step Step.PULL\n"
    )


def _my_step_callback(info: StepInfo) -> bool:
    msg = getattr(info, "message")
    print(msg)
    return True


# Test the update action separately because it's only defined
# for steps PULL and BUILD.


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize(
    "action_type", list(set(ActionType) - {ActionType.UPDATE, ActionType.REAPPLY})
)
def test_callback_pre(tmpdir, capfd, step, action_type):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=action_type))

    out, err = capfd.readouterr()
    assert not err
    if action_type == ActionType.SKIP:
        assert not out
    else:
        assert out == f"callback\nstep {step!r}\n"


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize(
    "action_type", list(set(ActionType) - {ActionType.UPDATE, ActionType.REAPPLY})
)
def test_callback_post(tmpdir, capfd, step, action_type):
    callbacks.register_post_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=action_type))

    out, err = capfd.readouterr()
    assert not err
    if action_type == ActionType.SKIP:
        assert not out
    else:
        assert out == f"step {step!r}\ncallback\n"


_update_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        source: .
        override-pull: echo "step Step.PULL"
        overlay-script: echo "step Step.OVERLAY"
        override-build: echo "step Step.BUILD"
        override-stage: echo "step Step.STAGE"
        override-prime: echo "step Step.PRIME"
    """
)


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD])
def test_update_callback_pre(tmpdir, capfd, step):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    out, err = capfd.readouterr()
    assert not err
    assert out == f"callback\nstep {step!r}\n"


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD])
def test_update_callback_post(tmpdir, capfd, step):
    callbacks.register_post_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    out, err = capfd.readouterr()
    assert not err
    assert out == f"step {step!r}\ncallback\n"


@pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
def test_invalid_update_callback_pre(tmpdir, step):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx, pytest.raises(errors.InvalidAction) as raised:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    name = step.name.lower()
    assert raised.value.message == f"cannot update step {name!r} of 'foo'"


@pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
def test_invalid_update_callback_post(tmpdir, step):
    callbacks.register_post_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="callback",
    )

    with lf.action_executor() as ctx, pytest.raises(errors.InvalidAction) as raised:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    name = step.name.lower()
    assert raised.value.message == f"cannot update step {name!r} of 'foo'"


def _my_exec_callback(info: ProjectInfo, part_list: List[Part]) -> None:
    for part in part_list:
        print(f"{part.name}: {getattr(info, 'message')}")


_exec_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        override-pull: echo "foo Step.PULL"
        overlay-script: echo "foo Step.OVERLAY"
        override-build: echo "foo Step.BUILD"
        override-stage: echo "foo Step.STAGE"
        override-prime: echo "foo Step.PRIME"
      bar:
        plugin: nil
        override-pull: echo "bar Step.PULL"
        overlay-script: echo "bar Step.OVERLAY"
        override-build: echo "bar Step.BUILD"
        override-stage: echo "bar Step.STAGE"
        override-prime: echo "bar Step.PRIME"
    """
)


def test_callback_prologue(tmpdir, capfd):
    callbacks.register_prologue(_my_exec_callback)

    parts = yaml.safe_load(_exec_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="prologue",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == "bar: prologue\nfoo: prologue\nfoo Step.PULL\n"


def test_callback_epilogue(tmpdir, capfd):
    callbacks.register_epilogue(_my_exec_callback)

    parts = yaml.safe_load(_exec_yaml)
    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test_callback",
        cache_dir=tmpdir,
        work_dir=tmpdir,
        base_layer_dir=tmpdir,
        base_layer_hash=b"hash",
        message="epilogue",
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == "foo Step.PULL\nbar: epilogue\nfoo: epilogue\n"
