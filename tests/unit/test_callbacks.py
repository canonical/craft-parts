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

from collections.abc import Generator
from pathlib import Path

import pytest
from craft_parts import callbacks, errors
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


def _callback_1(info: StepInfo) -> bool:
    greet = info.greet
    print(f"{greet} callback 1")
    return True


def _callback_2(info: StepInfo) -> bool:
    greet = info.greet
    print(f"{greet} callback 2")
    return False


def _callback_3(info: ProjectInfo) -> None:
    greet = info.greet
    print(f"{greet} callback 3")


def _callback_4(info: ProjectInfo) -> None:
    greet = info.greet
    print(f"{greet} callback 4")


def _callback_filter_1(info: ProjectInfo) -> list[str]:
    greet = info.greet
    print(f"{greet} filter 1")
    return ["a", "b", "c"]


def _callback_filter_2(info: ProjectInfo) -> Generator[str, None, None]:
    greet = info.greet
    print(f"{greet} filter 2")
    return (i for i in ["d", "e", "f"])


def _callback_overlay_1(overlay_dir: Path, info: ProjectInfo) -> None:
    greet = info.greet
    print(f"{overlay_dir} {greet} 1")


def _callback_overlay_2(overlay_dir: Path, info: ProjectInfo) -> None:
    greet = info.greet
    print(f"{overlay_dir} {greet} 2")


class TestCallbackRegistration:
    """Test different scenarios of callback function registration."""

    def setup_method(self):
        callbacks.unregister_all()

    def teardown_class(self):
        callbacks.unregister_all()

    def test_register_pre_step(self):
        callbacks.register_pre_step(_callback_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_pre_step(_callback_1)
        assert raised.value.message == (
            "callback function '_callback_1' is already registered."
        )

        # But we can register a different one
        callbacks.register_pre_step(_callback_2)

    def test_register_post_step(self):
        callbacks.register_post_step(_callback_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_post_step(_callback_1)
        assert raised.value.message == (
            "callback function '_callback_1' is already registered."
        )

        # But we can register a different one
        callbacks.register_post_step(_callback_2)

    def test_register_prologue(self):
        callbacks.register_prologue(_callback_3)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_prologue(_callback_3)
        assert raised.value.message == (
            "callback function '_callback_3' is already registered."
        )

        # But we can register a different one
        callbacks.register_prologue(_callback_4)

    def test_register_epilogue(self):
        callbacks.register_epilogue(_callback_3)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_epilogue(_callback_3)
        assert raised.value.message == (
            "callback function '_callback_3' is already registered."
        )

        # But we can register a different one
        callbacks.register_epilogue(_callback_4)

    def test_register_stage_packages_filters(self):
        callbacks.register_stage_packages_filter(_callback_filter_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_stage_packages_filter(_callback_filter_1)
        assert raised.value.message == (
            "callback function '_callback_filter_1' is already registered."
        )

        # But we can register a different one
        callbacks.register_stage_packages_filter(_callback_filter_2)

    def test_register_configure_overlay(self):
        callbacks.register_configure_overlay(_callback_overlay_1)

        # A callback function shouldn't be registered again
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_configure_overlay(_callback_overlay_1)
        assert raised.value.message == (
            "callback function '_callback_overlay_1' is already registered."
        )

        # But we can register a different one
        callbacks.register_configure_overlay(_callback_overlay_2)

    def test_register_both_pre_and_post(self):
        callbacks.register_pre_step(_callback_1)
        callbacks.register_post_step(_callback_1)

    def test_register_both_prologue_and_epilogue(self):
        callbacks.register_prologue(_callback_3)
        callbacks.register_epilogue(_callback_3)

    def test_unregister_all(self):
        callbacks.register_stage_packages_filter(_callback_filter_1)
        callbacks.register_stage_packages_filter(_callback_filter_2)
        callbacks.register_configure_overlay(_callback_overlay_1)
        callbacks.register_configure_overlay(_callback_overlay_2)
        callbacks.register_pre_step(_callback_1)
        callbacks.register_post_step(_callback_1)
        callbacks.register_prologue(_callback_3)
        callbacks.register_epilogue(_callback_3)
        callbacks.unregister_all()
        callbacks.register_stage_packages_filter(_callback_filter_1)
        callbacks.register_stage_packages_filter(_callback_filter_2)
        callbacks.register_configure_overlay(_callback_overlay_1)
        callbacks.register_configure_overlay(_callback_overlay_2)
        callbacks.register_pre_step(_callback_1)
        callbacks.register_post_step(_callback_1)
        callbacks.register_prologue(_callback_3)
        callbacks.register_epilogue(_callback_3)

    def test_register_steps(self):
        callbacks.register_pre_step(_callback_1, step_list=[Step.PULL, Step.BUILD])

        # A callback function shouldn't be registered again, even for a different step
        with pytest.raises(errors.CallbackRegistrationError) as raised:
            callbacks.register_pre_step(_callback_1, step_list=[Step.PRIME])
        assert raised.value.message == (
            "callback function '_callback_1' is already registered."
        )


class TestCallbackExecution:
    """Test different scenarios of callback function execution."""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        part = Part("foo", {})
        self._project_info = ProjectInfo(
            application_name="test",
            cache_dir=Path(),
            target_arch="x86_64",
            parallel_build_count=4,
            local_plugins_dir=None,
            greet="hello",
        )
        self._part_info = PartInfo(project_info=self._project_info, part=part)
        self._step_info = StepInfo(part_info=self._part_info, step=Step.BUILD)
        callbacks.unregister_all()

    def teardown_class(self):
        callbacks.unregister_all()

    def test_run_pre_step(self, capfd):
        callbacks.register_pre_step(_callback_1)
        callbacks.register_pre_step(_callback_2)
        callbacks.run_pre_step(self._step_info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 1\nhello callback 2\n"

    def test_run_post_step(self, capfd):
        callbacks.register_post_step(_callback_1)
        callbacks.register_post_step(_callback_2)
        callbacks.run_post_step(self._step_info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 1\nhello callback 2\n"

    def test_run_prologue(self, capfd):
        callbacks.register_prologue(_callback_3)
        callbacks.register_prologue(_callback_4)
        callbacks.run_prologue(self._project_info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 3\nhello callback 4\n"

    def test_run_epilogue(self, capfd):
        callbacks.register_epilogue(_callback_3)
        callbacks.register_epilogue(_callback_4)
        callbacks.run_epilogue(self._project_info)
        out, err = capfd.readouterr()
        assert not err
        assert out == "hello callback 3\nhello callback 4\n"

    @pytest.mark.parametrize(
        ("funcs", "result", "message"),
        [
            ([_callback_filter_1], {"a", "b", "c"}, "hello filter 1\n"),
            ([_callback_filter_2], {"d", "e", "f"}, "hello filter 2\n"),
            (
                [_callback_filter_1, _callback_filter_2],
                {"a", "b", "c", "d", "e", "f"},
                "hello filter 1\nhello filter 2\n",
            ),
        ],
    )
    def test_filter_package_list(self, capfd, funcs, result, message):
        for fn in funcs:
            callbacks.register_stage_packages_filter(fn)
        res = callbacks.get_stage_packages_filters(self._project_info)
        assert res == result

        out, err = capfd.readouterr()
        assert not err
        assert out == message

    def test_configure_callback(self, capfd):
        callbacks.register_configure_overlay(_callback_overlay_1)
        callbacks.register_configure_overlay(_callback_overlay_2)

        overlay_dir = Path("/overlay/mount")
        callbacks.run_configure_overlay(overlay_dir, self._project_info)

        out, err = capfd.readouterr()
        assert not err
        assert out == "/overlay/mount hello 1\n/overlay/mount hello 2\n"
