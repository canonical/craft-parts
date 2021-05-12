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

import os
from pathlib import Path
from unittest.mock import ANY

import pytest

from craft_parts import errors, packages
from craft_parts.executor.part_handler import PartHandler
from craft_parts.executor.step_handler import StepContents
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step


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
        self._part_info = PartInfo(ProjectInfo(), self._part)
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
    def test_run_step_scriptlet(self, capfd, step, scriptlet):
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello"})
        part_info = PartInfo(ProjectInfo(), p1)
        step_info = StepInfo(part_info, step=step)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        handler._run_step(
            step_info=step_info, scriptlet_name=scriptlet, work_dir=Path()
        )
        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == ""


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package handling."""

    def test_fetch_stage_packages(self, mocker):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        part_info = PartInfo(ProjectInfo(), p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result == ["pkg1", "pkg2"]

    def test_fetch_stage_packages_none(self, mocker):
        p1 = Part("p1", {"plugin": "nil"})
        part_info = PartInfo(ProjectInfo(), p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result is None

    def test_fetch_stage_packages_error(self, mocker):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            side_effect=packages.errors.PackageNotFound("pkg1"),
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        part_info = PartInfo(ProjectInfo(), p1)
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
        part_info = PartInfo(ProjectInfo(), p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        result = handler._fetch_stage_snaps()
        assert result == ["word-salad"]
        mock_download_snaps.assert_called_once_with(
            snaps_list=["word-salad"],
            directory=os.path.join(new_dir, "parts/p1/stage_snaps"),
        )

    def test_fetch_stage_snaps_none(self, mocker):
        p1 = Part("p1", {"plugin": "nil"})
        part_info = PartInfo(ProjectInfo(), p1)
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
        part_info = PartInfo(ProjectInfo(), p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])

        state = handler._run_pull(StepInfo(part_info, Step.PULL))
        getpkg.assert_called_once_with(
            application_name="craft_parts",
            base=ANY,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            target_arch=ANY,
        )

        assert state.assets["stage-packages"] == ["pkg1", "pkg2"]

        handler._run_build(StepInfo(part_info, Step.BUILD))
        unpack.assert_called_once()

    def test_unpack_stage_snaps(self, mocker, new_dir):
        mock_snap_provision = mocker.patch(
            "craft_parts.sources.snap_source.SnapSource.provision",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["snap1"]})
        part_info = PartInfo(ProjectInfo(), p1)
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

    def test_get_build_packages(self):
        p1 = Part(
            "p1", {"plugin": "make", "source": "a.tgz", "build-packages": ["pkg1"]}
        )
        part_info = PartInfo(ProjectInfo(), p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])
        assert sorted(handler._build_packages) == ["gcc", "make", "pkg1", "tar"]

    def test_get_build_snaps(self):
        p1 = Part("p1", {"plugin": "nil", "build-snaps": ["word-salad"]})
        part_info = PartInfo(ProjectInfo(), p1)
        handler = PartHandler(p1, part_info=part_info, part_list=[p1])
        assert handler._build_snaps == ["word-salad"]
