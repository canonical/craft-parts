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
import os
from pathlib import Path
from typing import cast
from unittest.mock import call

import pytest

from craft_parts import errors, packages
from craft_parts.actions import Action, ActionType
from craft_parts.executor import filesets, part_handler
from craft_parts.executor.part_handler import PartHandler
from craft_parts.executor.step_handler import StepContents
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step
from craft_parts.utils import os_utils

# pylint: disable=too-many-lines


@pytest.mark.usefixtures("new_dir")
class TestPartHandling:
    """Verify the part handler step processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {
                "plugin": "nil",
                "source": ".",
                "stage-packages": ["pkg1"],
                "stage-snaps": ["snap1"],
                "build-packages": ["pkg3"],
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        self._mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self._mock_mount_overlayfs = mocker.patch(
            "craft_parts.utils.os_utils.mount_overlayfs"
        )
        self._mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")
        # pylint: enable=attribute-defined-outside-init

    def test_run_pull(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_pull")
        mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        mocker.patch("craft_parts.packages.snaps.download_snaps")
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mock_run_step = mocker.spy(PartHandler, "_run_step")

        step_info = StepInfo(self._part_info, Step.PULL)
        state = self._handler._run_pull(step_info, stdout=None, stderr=None)
        assert state == states.PullState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            assets={
                "stage-packages": ["pkg1", "pkg2"],
                "stage-snaps": ["snap1"],
                "source-details": None,
            },
        )

        assert mock_run_step.mock_calls == [
            call(
                self._handler,
                step_info=step_info,
                scriptlet_name="override-pull",
                work_dir=new_dir / "parts/foo/src",
                stdout=None,
                stderr=None,
            )
        ]

    def test_run_pull_subdir(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_pull")
        mock_run_step = mocker.spy(PartHandler, "_run_step")

        part = Part(
            "foo",
            {
                "plugin": "nil",
                "source": ".",
                "source-subdir": "some/subdir",
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(project_info=info, part_list=[part], base_layer_dir=None)
        part_info = PartInfo(info, part)
        handler = PartHandler(
            part,
            part_info=part_info,
            part_list=[part],
            overlay_manager=ovmgr,
        )

        step_info = StepInfo(part_info, Step.PULL)
        handler._run_pull(step_info, stdout=None, stderr=None)
        assert mock_run_step.mock_calls == [
            call(
                handler,
                step_info=step_info,
                scriptlet_name="override-pull",
                work_dir=Path(new_dir, "parts/foo/src/some/subdir"),
                stdout=None,
                stderr=None,
            )
        ]

    def test_run_build(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")
        mocker.patch(
            "craft_parts.packages.Repository.get_installed_packages",
            return_value=["hello=2.10"],
        )
        mocker.patch(
            "craft_parts.packages.snaps.get_installed_snaps",
            return_value=["snapcraft=6466"],
        )
        mocker.patch("subprocess.check_output", return_value=b"os-info")
        mock_run_step = mocker.spy(PartHandler, "_run_step")

        step_info = StepInfo(self._part_info, Step.BUILD)
        state = self._handler._run_build(step_info, stdout=None, stderr=None)
        assert state == states.BuildState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            assets={
                "build-packages": ["pkg3"],
                "build-snaps": [],
                "uname": "os-info",
                "installed-packages": ["hello=2.10"],
                "installed-snaps": ["snapcraft=6466"],
            },
            overlay_hash="6554e32fa718d54160d0511b36f81458e4cb2357",
        )

        assert mock_run_step.mock_calls == [
            call(
                self._handler,
                step_info=step_info,
                scriptlet_name="override-build",
                work_dir=Path(new_dir, "parts/foo/build"),
                stdout=None,
                stderr=None,
            )
        ]

        assert self._mock_mount_overlayfs.mock_calls == []
        assert self._mock_umount.mock_calls == []

    def test_run_build_subdir(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")
        mock_run_step = mocker.spy(PartHandler, "_run_step")

        part = Part(
            "foo",
            {
                "plugin": "nil",
                "source": ".",
                "source-subdir": "some/subdir",
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(project_info=info, part_list=[part], base_layer_dir=None)
        part_info = PartInfo(info, part)
        handler = PartHandler(
            part,
            part_info=part_info,
            part_list=[part],
            overlay_manager=ovmgr,
        )

        step_info = StepInfo(self._part_info, Step.BUILD)
        handler._run_build(step_info, stdout=None, stderr=None)

        assert mock_run_step.mock_calls == [
            call(
                handler,
                step_info=step_info,
                scriptlet_name="override-build",
                work_dir=Path(new_dir, "parts/foo/build/some/subdir"),
                stdout=None,
                stderr=None,
            )
        ]

    @pytest.mark.usefixtures("new_dir")
    @pytest.mark.parametrize("out_of_source", [True, False])
    def test_run_build_out_of_source_behavior(self, mocker, out_of_source):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")
        mocker.patch(
            "craft_parts.packages.Repository.get_installed_packages",
            return_value=["hello=2.10"],
        )
        mocker.patch(
            "craft_parts.packages.snaps.get_installed_snaps",
            return_value=["snapcraft=6466"],
        )
        mocker.patch("subprocess.check_output", return_value=b"os-info")

        mocker.patch(
            "craft_parts.plugins.base.Plugin.get_out_of_source_build",
            return_value=out_of_source,
        )

        self._part_info.part_src_dir.mkdir(parents=True)
        source_file = self._part_info.part_src_dir / "source.c"
        source_file.write_text('printf("hello\n");', encoding="UTF-8")

        self._handler._run_build(
            StepInfo(self._part_info, Step.BUILD), stdout=None, stderr=None
        )

        # Check that 'source.c' exists in the source dir but not build dir.
        assert (self._part_info.part_src_dir / "source.c").exists()
        assert (
            self._part_info.part_build_dir / "source.c"
        ).exists() is not out_of_source

    def test_run_build_without_overlay_visibility(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")

        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        part_info = PartInfo(info, p1)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        handler._run_build(StepInfo(part_info, Step.BUILD), stdout=None, stderr=None)

        assert self._mock_mount_overlayfs.mock_calls == []

    def test_run_stage(self, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_stage",
            return_value=StepContents({"file"}, {"dir"}),
        )

        state = self._handler._run_stage(
            StepInfo(self._part_info, Step.STAGE), stdout=None, stderr=None
        )
        assert state == states.StageState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
            overlay_hash="6554e32fa718d54160d0511b36f81458e4cb2357",
        )

    def test_run_prime(self, new_dir, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_prime",
            return_value=StepContents({"file"}, {"dir"}),
        )
        mocker.patch("os.getxattr", new=lambda x, y: b"pkg")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            self._part,
            track_stage_packages=True,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )

        state = handler._run_prime(
            StepInfo(self._part_info, Step.PRIME), stdout=None, stderr=None
        )
        assert state == states.PrimeState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
            primed_stage_packages={"pkg"},
        )

    def test_run_prime_dont_track_packages(self, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_prime",
            return_value=StepContents({"file"}, {"dir"}),
        )
        mocker.patch("os.getxattr", new=lambda x, y: b"pkg")

        state = self._handler._run_prime(
            StepInfo(self._part_info, Step.PRIME), stdout=None, stderr=None
        )
        assert state == states.PrimeState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
            primed_stage_packages=set(),
        )

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet(self, new_dir, mocker, capfd, step, scriptlet):
        """If defined, scriptlets are executed instead of the built-in handler."""
        run_builtin_mock = mocker.patch(
            "craft_parts.executor.step_handler.StepHandler.run_builtin"
        )
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler._run_step(
            step_info=step_info,
            scriptlet_name=scriptlet,
            work_dir=Path(),
            stdout=None,
            stderr=None,
        )
        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == "+ echo hello\n"
        assert run_builtin_mock.mock_calls == []

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_empty_scriptlet(self, new_dir, mocker, step, scriptlet):
        """Even empty scriptlets are executed instead of the built-in handler."""
        run_builtin_mock = mocker.patch(
            "craft_parts.executor.step_handler.StepHandler.run_builtin"
        )
        p1 = Part("p1", {"plugin": "nil", scriptlet: ""})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler._run_step(
            step_info=step_info,
            scriptlet_name=scriptlet,
            work_dir=Path(),
            stdout=None,
            stderr=None,
        )
        assert run_builtin_mock.mock_calls == []

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_undefined_scriptlet(self, new_dir, mocker, step, scriptlet):
        """If scriptlets are not defined, execute the built-in handler."""
        run_builtin_mock = mocker.patch(
            "craft_parts.executor.step_handler.StepHandler.run_builtin"
        )
        p1 = Part("p1", {"plugin": "nil", scriptlet: None})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler._run_step(
            step_info=step_info,
            scriptlet_name=scriptlet,
            work_dir=Path(),
            stdout=None,
            stderr=None,
        )
        assert run_builtin_mock.mock_calls == [call()]

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet_streams(self, new_dir, capfd, step, scriptlet):
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello; echo goodbye >&2"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        output_path = Path("output.txt")
        error_path = Path("error.txt")

        with output_path.open("w") as output, error_path.open("w") as error:
            handler._run_step(
                step_info=step_info,
                scriptlet_name=scriptlet,
                work_dir=Path(),
                stdout=output,
                stderr=error,
            )

        out, err = capfd.readouterr()
        assert out == ""
        assert err == ""
        assert output_path.read_text() == "hello\n"
        assert error_path.read_text() == "+ echo hello\n+ echo goodbye\ngoodbye\n"


@pytest.mark.usefixtures("new_dir")
class TestPartUpdateHandler:
    """Verify step update processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {
                "plugin": "dump",
                "source": "subdir",
            },
        )
        Path("subdir").mkdir()
        Path("subdir/foo.txt").write_text("content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        # pylint: enable=attribute-defined-outside-init

    def test_update_pull(self):
        self._handler.run_action(Action("foo", Step.PULL))

        source_file = Path("subdir/foo.txt")
        os_utils.TimedWriter.write_text(source_file, "change")
        Path("parts/foo/src/bar.txt").touch()

        self._handler.run_action(Action("foo", Step.PULL, ActionType.UPDATE))

        assert Path("parts/foo/src/foo.txt").read_text() == "change"
        assert Path("parts/foo/src/bar.txt").exists()

    def test_update_pull_no_source(self, new_dir, caplog):
        caplog.set_level(logging.WARNING)
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part=p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        assert handler._source_handler is None

        # this shouldn't fail
        handler.run_action(Action("p1", Step.PULL, ActionType.UPDATE))

        assert caplog.records[0].message == (
            "Update requested on part 'p1' without a source handler."
        )

    def test_update_pull_with_scriptlet(self, new_dir, capfd):
        p1 = Part("p1", {"plugin": "nil", "override-pull": "echo hello"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler.run_action(Action("foo", Step.PULL, ActionType.UPDATE))

        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == "+ echo hello\n"

    def test_update_build(self):
        self._handler._make_dirs()
        self._handler.run_action(Action("foo", Step.PULL))
        self._handler.run_action(Action("foo", Step.OVERLAY))
        self._handler.run_action(Action("foo", Step.BUILD))

        source_file = Path("subdir/foo.txt")
        os_utils.TimedWriter.write_text(source_file, "change")

        self._handler.run_action(Action("foo", Step.BUILD, ActionType.UPDATE))

        assert Path("parts/foo/install/foo.txt").read_text() == "change"

    def test_update_build_stage_packages(self, new_dir, mocker):
        def fake_unpack(**_):
            Path("parts/foo/install/hello").touch()

        mocker.patch(
            "craft_parts.packages.Repository.unpack_stage_packages", new=fake_unpack
        )
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )

        part = Part(
            "foo",
            {"plugin": "dump", "source": "subdir", "stage-packages": ["pkg"]},
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(project_info=info, part_list=[part], base_layer_dir=None)
        part_info = PartInfo(info, part)
        handler = PartHandler(
            part,
            part_info=part_info,
            part_list=[part],
            overlay_manager=ovmgr,
        )
        handler._make_dirs()
        handler.run_action(Action("foo", Step.PULL))
        handler.run_action(Action("foo", Step.OVERLAY))
        handler.run_action(Action("foo", Step.BUILD))

        assert Path("parts/foo/install/hello").exists()

        handler.run_action(Action("foo", Step.BUILD, ActionType.UPDATE))

        assert Path("parts/foo/install/hello").exists()

    @pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
    def test_update_invalid(self, step):
        with pytest.raises(errors.InvalidAction):
            self._handler.run_action(Action("foo", step, ActionType.UPDATE))


def _run_step_migration(handler: PartHandler, step: Step) -> None:
    if step > Step.STAGE:
        handler.run_action(Action("", Step.STAGE))
    handler.run_action(Action("", step))


@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler:
    """Verify step update processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part("foo", {"plugin": "dump", "source": "subdir"})
        Path("subdir/bar").mkdir(parents=True)
        Path("subdir/foo.txt").write_text("content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        "step,test_dir,state_file",
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install", "build"),
            (Step.STAGE, "stage", "stage"),
            (Step.PRIME, "prime", "prime"),
        ],
    )
    def test_clean_step(self, mocker, step, test_dir, state_file):
        self._handler._make_dirs()
        for each_step in step.previous_steps() + [step]:
            self._handler.run_action(Action("foo", each_step))

        assert Path(test_dir, "foo.txt").is_file()
        assert Path(test_dir, "bar").is_dir()
        assert Path(f"parts/foo/state/{state_file}").is_file()

        self._handler.clean_step(step)

        assert Path(test_dir, "foo.txt").is_file() is False
        assert Path(test_dir, "bar").is_dir() is False
        assert Path(f"parts/foo/state/{state_file}").is_file() is False


@pytest.mark.usefixtures("new_dir")
class TestRerunStep:
    """Verify rerun actions."""

    @pytest.mark.parametrize("step", list(Step))
    def test_rerun_action(self, mocker, new_dir, step):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        mock_clean = mocker.patch(
            "craft_parts.executor.part_handler.PartHandler.clean_step"
        )
        mock_callback = mocker.patch("craft_parts.callbacks.run_pre_step")
        mock = mocker.MagicMock()
        mock.attach_mock(mock_clean, "clean_step")
        mock.attach_mock(mock_callback, "run_pre_step")

        handler.run_action(Action("p1", step, ActionType.RERUN))
        calls = [mocker.call.clean_step(step=x) for x in [step] + step.next_steps()]
        calls.append(mocker.call.run_pre_step(mocker.ANY))
        mock.assert_has_calls(calls)


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package handling."""

    def test_fetch_stage_packages(self, mocker, new_dir):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result == ["pkg1", "pkg2"]

    def test_fetch_stage_packages_none(self, mocker, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result is None

    def test_fetch_stage_packages_error(self, mocker, new_dir):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            side_effect=packages.errors.PackageNotFound("pkg1"),
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        with pytest.raises(errors.StagePackageNotFound) as raised:
            handler._fetch_stage_packages(step_info=step_info)
        assert raised.value.part_name == "p1"
        assert raised.value.package_name == "pkg1"

    def test_pull_fetch_stage_packages_arch(self, mocker, new_dir):
        """Verify _run_pull fetches stage packages from the host architecture."""
        getpkg = mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1"],
        )

        part = Part("foo", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part)
        ovmgr = OverlayManager(project_info=info, part_list=[part], base_layer_dir=None)
        handler = PartHandler(
            part, part_info=part_info, part_list=[part], overlay_manager=ovmgr
        )

        handler._run_pull(StepInfo(part_info, Step.PULL), stdout=None, stderr=None)
        getpkg.assert_called_once_with(
            cache_dir=mocker.ANY,
            base=mocker.ANY,
            package_names=mocker.ANY,
            stage_packages_path=mocker.ANY,
            arch=part_info.host_arch,
        )

    def test_fetch_stage_snaps(self, mocker, new_dir):
        mock_download_snaps = mocker.patch(
            "craft_parts.packages.snaps.download_snaps",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_snaps()
        assert result == ["word-salad"]
        mock_download_snaps.assert_called_once_with(
            snaps_list=["word-salad"],
            directory=os.path.join(new_dir, "parts/p1/stage_snaps"),
        )

    def test_fetch_stage_snaps_none(self, mocker, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_snaps()
        assert result is None

    def test_unpack_stage_packages(self, mocker, new_dir):
        getpkg = mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        unpack = mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch("craft_parts.executor.part_handler.PartHandler._run_step")

        p1 = Part("foo", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        state = handler._run_pull(
            StepInfo(part_info, Step.PULL), stdout=None, stderr=None
        )
        getpkg.assert_called_once_with(
            cache_dir=new_dir,
            base=mocker.ANY,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            arch=mocker.ANY,
        )

        assert cast(states.PullState, state).assets["stage-packages"] == [
            "pkg1",
            "pkg2",
        ]

        handler._run_build(StepInfo(part_info, Step.BUILD), stdout=None, stderr=None)
        unpack.assert_called_once()

    def test_unpack_stage_snaps(self, mocker, new_dir):
        mock_snap_provision = mocker.patch(
            "craft_parts.sources.snap_source.SnapSource.provision",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["snap1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        Path("parts/p1/stage_snaps").mkdir(parents=True)
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/stage_snaps/snap1.snap").write_text("content")

        handler._unpack_stage_snaps()
        mock_snap_provision.assert_called_once_with(
            new_dir / "parts/p1/install",
            keep=True,
        )

    def test_get_build_packages(self, new_dir):
        p1 = Part(
            "p1", {"plugin": "make", "source": "a.tgz", "build-packages": ["pkg1"]}
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert sorted(handler.build_packages) == ["gcc", "make", "pkg1", "tar"]

    def test_get_build_packages_with_source_type(self, new_dir):
        p1 = Part(
            "p1",
            {
                "plugin": "make",
                "source": "source",
                "source-type": "git",
                "build-packages": ["pkg1"],
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert sorted(handler.build_packages) == ["gcc", "git", "make", "pkg1"]

    def test_get_build_snaps(self, new_dir):
        p1 = Part("p1", {"plugin": "nil", "build-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert handler.build_snaps == ["word-salad"]


class TestFileFilter:
    """File filter test cases."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        Path("destdir").mkdir()
        Path("destdir/dir1").mkdir()
        Path("destdir/dir1/dir2").mkdir()
        Path("destdir/file1").touch()
        Path("destdir/file2").touch()
        Path("destdir/dir1/file3").touch()
        Path("destdir/file4").symlink_to("file2")
        Path("destdir/dir3").symlink_to("dir1")

    def test_apply_file_filter_empty(self, new_dir):
        destdir = Path("destdir")
        fileset = filesets.Fileset([])
        files, dirs = filesets.migratable_filesets(fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_file(self, new_dir):
        destdir = Path("destdir")
        fileset = filesets.Fileset(["-file1", "-dir1/file3"])
        files, dirs = filesets.migratable_filesets(fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").exists() is False
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").exists() is False
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_dir(self, new_dir):
        destdir = Path("destdir")
        fileset = filesets.Fileset(["-dir1", "-dir1/dir2"])
        files, dirs = filesets.migratable_filesets(fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1").exists() is False
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_symlink(self, new_dir):
        destdir = Path("destdir")
        fileset = filesets.Fileset(["-file4", "-dir3"])
        files, dirs = filesets.migratable_filesets(fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").exists() is False
        assert Path("destdir/dir3").exists() is False

    def test_apply_file_filter_keep_file(self, new_dir):
        destdir = Path("destdir")
        fileset = filesets.Fileset(["dir1/file3"])
        files, dirs = filesets.migratable_filesets(fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").exists() is False
        assert Path("destdir/file2").exists() is False
        assert Path("destdir/dir1/dir2").exists() is False
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").exists() is False
        assert Path("destdir/dir3").exists() is False


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify helper functions."""

    def test_remove_file(self):
        test_file = Path("foo.txt")
        test_file.write_text("content")
        assert test_file.exists()

        part_handler._remove(test_file)
        assert test_file.is_file() is False

    def test_remove_symlink(self):
        test_link = Path("foo")
        test_link.symlink_to("target")
        assert test_link.is_symlink()

        part_handler._remove(test_link)
        assert test_link.exists() is False

    def test_remove_dir(self):
        test_dir = Path("bar")
        test_dir.mkdir()
        assert test_dir.is_dir()

        part_handler._remove(test_dir)
        assert test_dir.exists() is False

    def test_remove_non_existent(self):
        # this should not raise and exception
        part_handler._remove(Path("not_here"))
