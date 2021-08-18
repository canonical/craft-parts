# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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
import stat
from pathlib import Path

import pytest

from craft_parts.actions import Action
from craft_parts.executor import filesets, migration, part_handler
from craft_parts.executor.filesets import Fileset
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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
        migration.migrate_files(
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


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify helper functions."""

    def test_clean_shared_area(self, new_dir):
        p1 = Part("p1", {"plugin": "dump", "source": "subdir1"})
        Path("subdir1").mkdir()
        Path("subdir1/foo.txt").write_text("content")

        p2 = Part("p2", {"plugin": "dump", "source": "subdir2"})
        Path("subdir2").mkdir()
        Path("subdir2/foo.txt").write_text("content")
        Path("subdir2/bar.txt").write_text("other content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)

        handler1 = part_handler.PartHandler(
            p1, part_info=PartInfo(info, part=p1), part_list=[p1, p2]
        )
        handler2 = part_handler.PartHandler(
            p2, part_info=PartInfo(info, part=p2), part_list=[p1, p2]
        )

        for step in [Step.PULL, Step.BUILD, Step.STAGE]:
            handler1.run_action(Action("p1", step))
            handler2.run_action(Action("p2", step))

        part_states = part_handler._load_part_states(Step.STAGE, part_list=[p1, p2])

        assert Path("stage/foo.txt").is_file()
        assert Path("stage/bar.txt").is_file()

        migration.clean_shared_area(
            part_name="p1", shared_dir=p1.stage_dir, part_states=part_states
        )

        assert Path("stage/foo.txt").is_file()  # remains, it's shared with p2
        assert Path("stage/bar.txt").is_file()

        migration.clean_shared_area(
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
        handler = part_handler.PartHandler(p1, part_info=part_info, part_list=[p1])

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        assert Path("stage/foo.txt").is_file()
        assert Path("stage/bar").is_dir()

        migration._clean_migrated_files({"foo.txt"}, {"bar"}, Path("stage"))

        assert Path("stage/foo.txt").exists() is False
        assert Path("stage/bar").exists() is False

    def test_clean_migrated_files_missing(self, new_dir):
        Path("subdir").mkdir()

        p1 = Part("p1", {"plugin": "dump", "source": "subdir"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part=p1)
        handler = part_handler.PartHandler(p1, part_info=part_info, part_list=[p1])

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        # this shouldn't raise an exception
        migration._clean_migrated_files({"foo.txt"}, {"bar"}, Path("stage"))
