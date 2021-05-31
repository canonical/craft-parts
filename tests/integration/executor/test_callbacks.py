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
        override-pull: echo "override Step.PULL"
        override-build: echo "override Step.BUILD"
        override-stage: echo "override Step.STAGE"
        override-prime: echo "override Step.PRIME"
    """
)


@pytest.mark.parametrize("step", list(Step))
def test_step_callback(tmpdir, capfd, step):
    callbacks.register_pre_step(_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_step_callback", work_dir=tmpdir
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
        f"override {step!r}\n"
    )


def test_prologue_callback(tmpdir, capfd):
    callbacks.register_prologue(_exec_callback)

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_prologue_callback", work_dir=tmpdir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == (
        "application_name = test_prologue_callback\n"
        "parts = foo\n"
        "override Step.PULL\n"
    )


def _my_step_callback(info: StepInfo) -> bool:
    msg = getattr(info, "message")
    print(msg)
    return True


# Test the update action separately because it's only defined
# for steps PULL and BUILD.


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize("action_type", list(set(ActionType) - {ActionType.UPDATE}))
def test_callback_pre(tmpdir, capfd, step, action_type):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=action_type))

    out, err = capfd.readouterr()
    assert not err
    if action_type == ActionType.SKIP:
        assert not out
    else:
        assert out == f"callback\noverride {step!r}\n"


@pytest.mark.parametrize("step", list(Step))
@pytest.mark.parametrize("action_type", list(set(ActionType) - {ActionType.UPDATE}))
def test_callback_post(tmpdir, capfd, step, action_type):
    callbacks.register_post_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=action_type))

    out, err = capfd.readouterr()
    assert not err
    if action_type == ActionType.SKIP:
        assert not out
    else:
        assert out == f"override {step!r}\ncallback\n"


_update_yaml = textwrap.dedent(
    """\
    parts:
      foo:
        plugin: nil
        source: .
        override-pull: echo "override Step.PULL"
        override-build: echo "override Step.BUILD"
        override-stage: echo "override Step.STAGE"
        override-prime: echo "override Step.PRIME"
    """
)


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD])
def test_update_callback_pre(tmpdir, capfd, step):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    out, err = capfd.readouterr()
    assert not err
    assert out == f"callback\noverride {step!r}\n"


@pytest.mark.parametrize("step", [Step.PULL, Step.BUILD])
def test_update_callback_post(tmpdir, capfd, step):
    callbacks.register_post_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", step, action_type=ActionType.UPDATE))

    out, err = capfd.readouterr()
    assert not err
    assert out == f"override {step!r}\ncallback\n"


@pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
def test_invalid_update_callback_pre(tmpdir, step):
    callbacks.register_pre_step(_my_step_callback, step_list=[step])

    parts = yaml.safe_load(_update_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
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
        parts, application_name="test_callback", work_dir=tmpdir, message="callback"
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
        override-build: echo "foo Step.BUILD"
        override-stage: echo "foo Step.STAGE"
        override-prime: echo "foo Step.PRIME"
      bar:
        plugin: nil
        override-pull: echo "bar Step.PULL"
        override-build: echo "bar Step.BUILD"
        override-stage: echo "bar Step.STAGE"
        override-prime: echo "bar Step.PRIME"
    """
)


def test_callback_prologue(tmpdir, capfd):
    callbacks.register_prologue(_my_exec_callback)

    parts = yaml.safe_load(_exec_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="prologue"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == "foo: prologue\nbar: prologue\nfoo Step.PULL\n"


def test_callback_epilogue(tmpdir, capfd):
    callbacks.register_epilogue(_my_exec_callback)

    parts = yaml.safe_load(_exec_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_callback", work_dir=tmpdir, message="epilogue"
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    out, err = capfd.readouterr()
    assert not err
    assert out == "foo Step.PULL\nfoo: epilogue\nbar: epilogue\n"
