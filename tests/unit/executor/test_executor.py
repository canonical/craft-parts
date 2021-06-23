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

from pathlib import Path

import pytest

from craft_parts import callbacks
from craft_parts.actions import Action
from craft_parts.executor import ExecutionContext, Executor
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


@pytest.mark.usefixtures("new_dir")
class TestExecutor:
    """Verify executor class methods."""

    def test_clean(self):
        p1 = Part("p1", {"plugin": "nil"})
        file1 = Path("parts/p1/src/foo.txt")
        file1.parent.mkdir(parents=True)
        file1.touch()

        p2 = Part("p2", {"plugin": "nil"})
        file2 = Path("parts/p2/src/bar.txt")
        file2.parent.mkdir(parents=True)
        file2.touch()

        assert file1.exists()
        assert file2.exists()

        e = Executor(project_info=ProjectInfo(), part_list=[p1, p2])
        e.clean(Step.PULL)

        assert file1.exists() is False
        assert file2.exists() is False

    def test_clean_part(self):
        p1 = Part("p1", {"plugin": "nil"})
        file1 = Path("parts/p1/src/foo.txt")
        file1.parent.mkdir(parents=True)
        file1.touch()

        p2 = Part("p2", {"plugin": "nil"})
        file2 = Path("parts/p2/src/bar.txt")
        file2.parent.mkdir(parents=True)
        file2.touch()

        assert file1.exists()
        assert file2.exists()

        e = Executor(project_info=ProjectInfo(), part_list=[p1, p2])
        e.clean(Step.PULL, part_names=["p1"])

        assert file1.exists() is False
        assert file2.exists()

        e.clean(Step.PULL, part_names=["p2"])

        assert file1.exists() is False
        assert file2.exists() is False


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package installation during the execution phase."""

    def test_install_build_packages(self, mocker):
        install = mocker.patch("craft_parts.packages.Repository.install_build_packages")

        p1 = Part("foo", {"plugin": "nil", "build-packages": ["pkg1"]})
        p2 = Part("bar", {"plugin": "nil", "build-packages": ["pkg2"]})

        e = Executor(project_info=ProjectInfo(), part_list=[p1, p2])
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2"])

    def test_install_extra_build_packages(self, mocker):
        install = mocker.patch("craft_parts.packages.Repository.install_build_packages")

        p1 = Part("foo", {"plugin": "nil", "build-packages": ["pkg1"]})
        p2 = Part("bar", {"plugin": "nil", "build-packages": ["pkg2"]})

        e = Executor(
            project_info=ProjectInfo(),
            part_list=[p1, p2],
            extra_build_packages=["pkg3"],
        )
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2", "pkg3"])

    def test_install_build_snaps(self, mocker):
        mocker.patch("craft_parts.packages.snaps.SnapPackage.get_store_snap_info")
        install = mocker.patch("craft_parts.packages.snaps.install_snaps")

        p1 = Part("foo", {"plugin": "nil", "build-snaps": ["snap1"]})
        p2 = Part("bar", {"plugin": "nil", "build-snaps": ["snap2"]})

        e = Executor(project_info=ProjectInfo(), part_list=[p1, p2])
        e.prologue()

        install.assert_called_once_with({"snap1", "snap2"})

    def test_install_build_snaps_in_container(self, mocker):
        mocker.patch(
            "craft_parts.utils.os_utils.is_inside_container", return_value=True
        )
        install = mocker.patch("craft_parts.packages.snaps.install_snaps")

        p1 = Part("foo", {"plugin": "nil", "build-snaps": ["snap1"]})
        p2 = Part("bar", {"plugin": "nil", "build-snaps": ["snap2"]})
        info = ProjectInfo()

        e = Executor(project_info=info, part_list=[p1, p2])
        e.prologue()

        install.assert_not_called()


@pytest.mark.usefixtures("new_dir")
class TestExecutionContext:
    """Verify execution context methods."""

    def setup_method(self):
        callbacks.unregister_all()

    def teardown_class(self):
        callbacks.unregister_all()

    def test_prologue(self, capfd):
        def cbf(info, part_list):
            print(f"prologue {info.custom} for {part_list[0].name}")

        callbacks.register_prologue(cbf)
        p1 = Part("p1", {"plugin": "nil", "override-build": "echo build"})
        e = Executor(project_info=ProjectInfo(custom="test"), part_list=[p1])

        with ExecutionContext(executor=e) as ctx:
            ctx.execute(Action("p1", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "prologue test for p1\nbuild\n"

    def test_epilogue(self, capfd):
        def cbf(info, part_list):
            print(f"epilogue {info.custom} for {part_list[0].name}")

        callbacks.register_epilogue(cbf)
        p1 = Part("p1", {"plugin": "nil", "override-build": "echo build"})
        e = Executor(project_info=ProjectInfo(custom="test"), part_list=[p1])

        with ExecutionContext(executor=e) as ctx:
            ctx.execute(Action("p1", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "build\nepilogue test for p1\n"
