# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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

    def test_clean(self, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        file1 = Path("parts/p1/src/foo.txt")
        file1.parent.mkdir(parents=True)
        file1.touch()

        p2 = Part("p2", {"plugin": "nil"})
        file2 = Path("parts/p2/src/bar.txt")
        file2.parent.mkdir(parents=True)
        file2.touch()

        stage_dir = Path("stage")
        stage_dir.mkdir()
        file3 = Path("stage/foobar.txt")
        file3.touch()

        assert file1.exists()
        assert file2.exists()
        assert file3.exists()

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        e = Executor(project_info=info, part_list=[p1, p2])
        e.clean(Step.PULL)

        assert file1.exists() is False
        assert file2.exists() is False
        assert file3.exists() is False
        assert stage_dir.exists() is False

    def test_clean_part(self, new_dir):
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

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        e = Executor(project_info=info, part_list=[p1, p2])
        e.clean(Step.PULL, part_names=["p1"])

        assert file1.exists() is False
        assert file2.exists()

        e.clean(Step.PULL, part_names=["p2"])

        assert file1.exists() is False
        assert file2.exists() is False


class TestPackages:
    """Verify package installation during the execution phase."""

    def test_install_packages(self, mocker, new_dir, partitions):
        install = mocker.patch("craft_parts.packages.Repository.install_packages")

        p1 = Part(
            "foo", {"plugin": "nil", "build-packages": ["pkg1"]}, partitions=partitions
        )
        p2 = Part(
            "bar",
            {"plugin": "nil", "build-packages": ["pkg2"]},
            partitions=partitions,
        )

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        e = Executor(project_info=info, part_list=[p1, p2])
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2"])

    def test_install_extra_build_packages(self, mocker, new_dir, partitions):
        install = mocker.patch("craft_parts.packages.Repository.install_packages")

        p1 = Part(
            "foo",
            {"plugin": "nil", "build-packages": ["pkg1"]},
            partitions=partitions,
        )
        p2 = Part(
            "bar",
            {"plugin": "nil", "build-packages": ["pkg2"]},
            partitions=partitions,
        )

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )

        e = Executor(
            project_info=info,
            part_list=[p1, p2],
            extra_build_packages=["pkg3"],
        )
        e.prologue()

        install.assert_called_once_with(["pkg1", "pkg2", "pkg3"])

    def test_install_build_snaps(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.packages.snaps.SnapPackage.get_store_snap_info")
        install = mocker.patch("craft_parts.packages.snaps.install_snaps")

        p1 = Part(
            "foo",
            {"plugin": "nil", "build-snaps": ["snap1"]},
            partitions=partitions,
        )
        p2 = Part(
            "bar",
            {"plugin": "nil", "build-snaps": ["snap2"]},
            partitions=partitions,
        )

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )

        e = Executor(project_info=info, part_list=[p1, p2])
        e.prologue()

        install.assert_called_once_with({"snap1", "snap2"})

    def test_install_build_snaps_in_container(self, mocker, new_dir, partitions):
        mocker.patch(
            "craft_parts.utils.os_utils.is_inside_container", return_value=True
        )
        install = mocker.patch("craft_parts.packages.snaps.install_snaps")

        p1 = Part(
            "foo",
            {"plugin": "nil", "build-snaps": ["snap1"]},
            partitions=partitions,
        )
        p2 = Part(
            "bar",
            {"plugin": "nil", "build-snaps": ["snap2"]},
            partitions=partitions,
        )

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )

        e = Executor(project_info=info, part_list=[p1, p2])
        e.prologue()

        install.assert_not_called()


class TestExecutionContext:
    """Verify execution context methods."""

    def setup_method(self):
        callbacks.unregister_all()

    def teardown_class(self):
        callbacks.unregister_all()

    def test_prologue(self, capfd, new_dir, partitions):
        def cbf(info):
            print(f"prologue {info.custom}")

        callbacks.register_prologue(cbf)
        p1 = Part(
            "p1",
            {"plugin": "nil", "override-build": "echo build"},
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test",
            cache_dir=new_dir,
            custom="custom",
            partitions=partitions,
        )
        e = Executor(project_info=info, part_list=[p1])

        with ExecutionContext(executor=e) as ctx:
            ctx.execute(Action("p1", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "prologue custom\nbuild\n"

    def test_epilogue(self, capfd, new_dir, partitions):
        def cbf(info):
            print(f"epilogue {info.custom}")

        callbacks.register_epilogue(cbf)
        p1 = Part(
            "p1",
            {"plugin": "nil", "override-build": "echo build"},
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test",
            cache_dir=new_dir,
            custom="custom",
            partitions=partitions,
        )
        e = Executor(project_info=info, part_list=[p1])

        with ExecutionContext(executor=e) as ctx:
            ctx.execute(Action("p1", Step.BUILD))

        captured = capfd.readouterr()
        assert captured.out == "build\nepilogue custom\n"

    def test_capture_stdout(self, capfd, new_dir, partitions):
        def cbf(info):
            print(f"prologue {info.custom}")

        callbacks.register_prologue(cbf)
        p1 = Part(
            "p1",
            {"plugin": "nil", "override-build": "echo out; echo err >&2"},
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test",
            cache_dir=new_dir,
            custom="custom",
            partitions=partitions,
        )
        e = Executor(project_info=info, part_list=[p1])

        output_path = Path("output.txt")
        error_path = Path("error.txt")

        with output_path.open("w") as output, error_path.open("w") as error:
            with ExecutionContext(executor=e) as ctx:
                ctx.execute(Action("p1", Step.BUILD), stdout=output, stderr=error)

        captured = capfd.readouterr()
        assert captured.out == "prologue custom\n"
        assert output_path.read_text() == "out\n"
        assert error_path.read_text() == "+ echo out\n+ echo err\nerr\n"
