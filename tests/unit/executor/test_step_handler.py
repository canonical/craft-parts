# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
import stat
from pathlib import Path
from typing import Dict, List, Set

import pytest

from craft_parts import plugins, sources
from craft_parts.dirs import ProjectDirs
from craft_parts.executor import filesets, step_handler
from craft_parts.executor.filesets import Fileset
from craft_parts.executor.step_handler import StepContents, StepHandler
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
        return {}

    def get_build_commands(self) -> List[str]:
        return ["hello"]


def _step_handler_for_step(step: Step) -> StepHandler:
    p1 = Part("p1", {"source": "."})
    dirs = ProjectDirs()
    info = ProjectInfo(project_dirs=dirs)
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=step)
    props = plugins.PluginProperties()
    plugin = FooPlugin(properties=props, part_info=part_info)
    source_handler = sources.get_source_handler(
        application_name="test",
        part=p1,
        project_dirs=dirs,
    )

    return StepHandler(
        part=p1,
        step_info=step_info,
        plugin=plugin,
        source_handler=source_handler,
    )


@pytest.mark.usefixtures("new_dir")
class TestStepHandlerBuiltins:
    """Verify the built-in handlers."""

    def test_run_builtin_pull(self, mocker):
        mock_source_pull = mocker.patch(
            "craft_parts.sources.local_source.LocalSource.pull"
        )

        sh = _step_handler_for_step(Step.PULL)
        result = sh.run_builtin()

        mock_source_pull.assert_called_once_with()
        assert result == StepContents()

    def test_run_builtin_build(self, new_dir, mocker):
        mock_run = mocker.patch("subprocess.run")

        Path("parts/p1/run").mkdir(parents=True)
        sh = _step_handler_for_step(Step.BUILD)
        result = sh.run_builtin()

        mock_run.assert_called_once_with(
            [Path(new_dir / "parts/p1/run/build.sh")],
            check=True,
            cwd=Path(new_dir / "parts/p1/build"),
        )
        assert result == StepContents()

    def test_run_builtin_stage(self, mocker):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage").mkdir()
        sh = _step_handler_for_step(Step.STAGE)
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_prime(self, mocker):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage/subdir").mkdir(parents=True)
        Path("stage/foo").write_text("content")
        Path("stage/subdir/bar").write_text("content")
        sh = _step_handler_for_step(Step.PRIME)
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_invalid(self):
        sh = _step_handler_for_step(999)  # type: ignore
        with pytest.raises(RuntimeError) as raised:
            sh.run_builtin()
        assert str(raised.value) == (
            "Request to run the built-in handler for an invalid step."
        )


@pytest.mark.usefixtures("new_dir")
class TestStepHandlerRunScriptlet:
    """Verify the scriptlet runner."""

    def test_run_scriptlet(self, new_dir, capfd):
        sh = _step_handler_for_step(Step.PULL)
        sh.run_scriptlet("echo hello world", scriptlet_name="name", work_dir=new_dir)
        captured = capfd.readouterr()
        assert captured.out == "hello world\n"

    # TODO: test ctl api server


@pytest.mark.usefixtures("new_dir")
class TestFileMigration:
    """Verify different migration scenarios."""

    def test_migrate_files_already_exists(self):
        os.makedirs("install")
        os.makedirs("stage")

        # Place the already-staged file
        with open("stage/foo", "w") as f:
            f.write("staged")

        # Place the to-be-staged file with the same name
        with open("install/foo", "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the staged file is the one that was staged last
        with open("stage/foo", "r") as f:
            assert (
                f.read() == "installed"
            ), "Expected staging to allow overwriting of already-staged files"

    def test_migrate_files_supports_no_follow_symlinks(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=False,
        )

        # Verify that the symlink was preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to still be a symlink."

        assert (
            os.readlink(os.path.join("stage", "bar")) == "foo"
        ), "Expected migrated 'bar' to point to 'foo'"

    def test_migrate_files_preserves_symlink_file(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'sym-a' to be a symlink."

    def test_migrate_files_no_follow_symlinks(self):
        os.makedirs("install/usr/bin")
        os.makedirs("stage")

        with open(os.path.join("install", "usr", "bin", "foo"), "w") as f:
            f.write("installed")

        os.symlink("usr/bin", os.path.join("install", "bin"))

        files, dirs = filesets.migratable_filesets(Fileset(["-usr"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert files == {"bin"}
        assert dirs == set()

        assert os.path.islink(
            os.path.join("stage", "bin")
        ), "Expected migrated 'bin' to be a symlink."

    def test_migrate_files_preserves_symlink_nested_file(self):
        os.makedirs(os.path.join("install", "a"))
        os.makedirs("stage")

        with open(os.path.join("install", "a", "foo"), "w") as f:
            f.write("installed")

        os.symlink(os.path.join("a", "foo"), os.path.join("install", "bar"))
        os.symlink(os.path.join("foo"), os.path.join("install", "a", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'sym-a' to be a symlink."

        assert os.path.islink(
            os.path.join("stage", "a", "bar")
        ), "Expected migrated 'a/bar' to be a symlink."

    def test_migrate_files_preserves_symlink_empty_dir(self):
        os.makedirs(os.path.join("install", "foo"))
        os.makedirs("stage")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

    def test_migrate_files_preserves_symlink_nonempty_dir(self):
        os.makedirs(os.path.join("install", "foo"))
        os.makedirs("stage")

        os.symlink("foo", os.path.join("install", "bar"))

        with open(os.path.join("install", "foo", "xfile"), "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

    def test_migrate_files_preserves_symlink_nested_dir(self):
        os.makedirs(os.path.join("install", "a", "b"))
        os.makedirs("stage")

        os.symlink(os.path.join("a", "b"), os.path.join("install", "bar"))
        os.symlink(os.path.join("b"), os.path.join("install", "a", "bar"))

        with open(os.path.join("install", "a", "b", "xfile"), "w") as f:
            f.write("installed")

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files, dirs=dirs, srcdir="install", destdir="stage"
        )

        # Verify that the symlinks were preserved
        assert os.path.islink(
            os.path.join("stage", "bar")
        ), "Expected migrated 'bar' to be a symlink."

        assert os.path.islink(
            os.path.join("stage", "a", "bar")
        ), "Expected migrated 'a/bar' to be a symlink."

    def test_migrate_files_supports_follow_symlinks(self):
        os.makedirs("install")
        os.makedirs("stage")

        with open(os.path.join("install", "foo"), "w") as f:
            f.write("installed")

        os.symlink("foo", os.path.join("install", "bar"))

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        # Verify that the symlink was preserved
        assert (
            os.path.islink(os.path.join("stage", "bar")) is False
        ), "Expected migrated 'bar' to no longer be a symlink."

        with open(os.path.join("stage", "bar"), "r") as f:
            assert (
                f.read() == "installed"
            ), "Expected migrated 'bar' to be a copy of 'foo'"

    def test_migrate_files_preserves_file_mode(self):
        os.makedirs("install")
        os.makedirs("stage")

        filepath = os.path.join("install", "foo")

        with open(filepath, "w") as f:
            f.write("installed")

        mode = os.stat(filepath).st_mode

        new_mode = 0o777
        os.chmod(filepath, new_mode)
        assert mode != new_mode

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(os.stat(os.path.join("stage", "foo")).st_mode)

    # TODO: add test_migrate_files_preserves_file_mode_chown_permissions

    def test_migrate_files_preserves_directory_mode(self):
        os.makedirs("install/foo")
        os.makedirs("stage")

        filepath = os.path.join("install", "foo", "bar")

        with open(filepath, "w") as f:
            f.write("installed")

        mode = os.stat(filepath).st_mode

        new_mode = 0o777
        assert mode != new_mode
        os.chmod(os.path.dirname(filepath), new_mode)
        os.chmod(filepath, new_mode)

        files, dirs = filesets.migratable_filesets(Fileset(["*"]), "install")
        step_handler._migrate_files(
            files=files,
            dirs=dirs,
            srcdir="install",
            destdir="stage",
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(os.stat(os.path.join("stage", "foo")).st_mode)
        assert new_mode == stat.S_IMODE(
            os.stat(os.path.join("stage", "foo", "bar")).st_mode
        )
