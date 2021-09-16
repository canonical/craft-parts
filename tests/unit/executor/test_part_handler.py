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

import logging
import os
from pathlib import Path
from typing import cast

import pytest

from craft_parts import errors, packages
from craft_parts.actions import Action, ActionType
from craft_parts.executor import part_handler
from craft_parts.executor.part_handler import PartHandler
from craft_parts.executor.step_handler import StepContents
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step
from craft_parts.utils import os_utils


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
                "stage-packages": ["pkg1"],
                "stage-snaps": ["snap1"],
                "build-packages": ["pkg3"],
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
        )
        # pylint: enable=attribute-defined-outside-init

    def test_run_pull(self, mocker):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_pull")
        mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        mocker.patch("craft_parts.packages.snaps.download_snaps")

        state = self._handler._run_pull(StepInfo(self._part_info, Step.PULL))
        assert state == states.PullState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            assets={
                "stage-packages": ["pkg1", "pkg2"],
                "stage-snaps": ["snap1"],
                "source-details": None,
            },
        )

    def test_run_build(self, mocker):
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

        state = self._handler._run_build(StepInfo(self._part_info, Step.BUILD))
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
        )

    def test_run_stage(self, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_stage",
            return_value=StepContents({"file"}, {"dir"}),
        )

        state = self._handler._run_stage(StepInfo(self._part_info, Step.STAGE))
        assert state == states.StageState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
        )

    def test_run_prime(self, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_prime",
            return_value=StepContents({"file"}, {"dir"}),
        )

        state = self._handler._run_prime(StepInfo(self._part_info, Step.PRIME))
        assert state == states.PrimeState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
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
    def test_run_step_scriptlet(self, new_dir, capfd, step, scriptlet):
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        handler._run_step(
            step_info=step_info, scriptlet_name=scriptlet, work_dir=Path()
        )
        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == ""


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
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        handler.run_action(Action("foo", Step.PULL, ActionType.UPDATE))

        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == ""

    def test_update_build(self):
        self._handler._make_dirs()
        self._handler.run_action(Action("foo", Step.PULL))
        self._handler.run_action(Action("foo", Step.BUILD))

        source_file = Path("subdir/foo.txt")
        os_utils.TimedWriter.write_text(source_file, "change")

        self._handler.run_action(Action("foo", Step.BUILD, ActionType.UPDATE))

        assert Path("parts/foo/install/foo.txt").read_text() == "change"

    @pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
    def test_update_invalid(self, step):
        with pytest.raises(errors.InvalidAction):
            self._handler.run_action(Action("foo", step, ActionType.UPDATE))


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
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
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
    def test_clean_step(self, step, test_dir, state_file):
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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result == ["pkg1", "pkg2"]

    def test_fetch_stage_packages_none(self, mocker, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        with pytest.raises(errors.StagePackageNotFound) as raised:
            handler._fetch_stage_packages(step_info=step_info)
        assert raised.value.part_name == "p1"
        assert raised.value.package_name == "pkg1"

    def test_fetch_stage_snaps(self, mocker, new_dir):
        mock_download_snaps = mocker.patch(
            "craft_parts.packages.snaps.download_snaps",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

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
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        state = handler._run_pull(StepInfo(part_info, Step.PULL))
        getpkg.assert_called_once_with(
            cache_dir=new_dir,
            base=mocker.ANY,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            target_arch=mocker.ANY,
        )

        assert cast(states.PullState, state).assets["stage-packages"] == [
            "pkg1",
            "pkg2",
        ]

        handler._run_build(StepInfo(part_info, Step.BUILD))
        unpack.assert_called_once()

    def test_unpack_stage_snaps(self, mocker, new_dir):
        mock_snap_provision = mocker.patch(
            "craft_parts.sources.snap_source.SnapSource.provision",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["snap1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        Path("parts/p1/stage_snaps").mkdir(parents=True)
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/stage_snaps/snap1.snap").write_text("content")

        handler._unpack_stage_snaps()
        mock_snap_provision.assert_called_once_with(
            str(new_dir / "parts/p1/install"),
            clean_target=False,
            keep=True,
        )

    def test_get_build_packages(self, new_dir):
        p1 = Part(
            "p1", {"plugin": "make", "source": "a.tgz", "build-packages": ["pkg1"]}
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])
        assert sorted(handler.build_packages) == ["gcc", "make", "pkg1", "tar"]

    def test_get_build_snaps(self, new_dir):
        p1 = Part("p1", {"plugin": "nil", "build-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])
        assert handler.build_snaps == ["word-salad"]


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

    def test_clean_shared_area(self, new_dir):
        p1 = Part("p1", {"plugin": "dump", "source": "subdir1"})
        Path("subdir1").mkdir()
        Path("subdir1/foo.txt").write_text("content")

        p2 = Part("p2", {"plugin": "dump", "source": "subdir2"})
        Path("subdir2").mkdir()
        Path("subdir2/foo.txt").write_text("content")
        Path("subdir2/bar.txt").write_text("other content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)

        handler1 = PartHandler(
            p1, part_info=PartInfo(info, part=p1), part_list=[p1, p2]
        )
        handler2 = PartHandler(
            p2, part_info=PartInfo(info, part=p2), part_list=[p1, p2]
        )

        for step in [Step.PULL, Step.BUILD, Step.STAGE]:
            handler1.run_action(Action("p1", step))
            handler2.run_action(Action("p2", step))

        part_states = part_handler._load_part_states(Step.STAGE, part_list=[p1, p2])

        assert Path("stage/foo.txt").is_file()
        assert Path("stage/bar.txt").is_file()

        part_handler._clean_shared_area(
            part_name="p1", shared_dir=p1.stage_dir, part_states=part_states
        )

        assert Path("stage/foo.txt").is_file()  # remains, it's shared with p2
        assert Path("stage/bar.txt").is_file()

        part_handler._clean_shared_area(
            part_name="p2", shared_dir=p2.stage_dir, part_states=part_states
        )

        assert Path("stage/foo.txt").exists() is False
        assert Path("stage/bar.txt").exists() is False

    def test_clean_migrated_files(self, new_dir):
        Path("subdir").mkdir()
        Path("subdir/foo.txt").touch()
        Path("subdir/bar").mkdir()

        p1 = Part("p1", {"plugin": "dump", "source": "subdir"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part=p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        assert Path("stage/foo.txt").is_file()
        assert Path("stage/bar").is_dir()

        part_handler._clean_migrated_files({"foo.txt"}, {"bar"}, Path("stage"))

        assert Path("stage/foo.txt").exists() is False
        assert Path("stage/bar").exists() is False

    def test_clean_migrated_files_missing(self, new_dir):
        Path("subdir").mkdir()

        p1 = Part("p1", {"plugin": "dump", "source": "subdir"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part=p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        # this shouldn't raise an exception
        part_handler._clean_migrated_files({"foo.txt"}, {"bar"}, Path("stage"))
