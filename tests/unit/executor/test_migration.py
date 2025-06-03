# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2025 Canonical Ltd.
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
from craft_parts import errors, features
from craft_parts.actions import Action
from craft_parts.executor import filesets, migration, part_handler
from craft_parts.executor.filesets import Fileset
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part
from craft_parts.permissions import Permissions
from craft_parts.steps import Step


@pytest.mark.usefixtures("new_dir")
class TestFileMigration:
    """Verify different migration scenarios."""

    def test_migrate_files_already_exists(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        install_dir.mkdir()
        stage_dir.mkdir()

        # Place the already-staged file
        Path(stage_dir, "foo").write_text("staged")

        # Place the to-be-staged file with the same name
        Path(install_dir, "foo").write_text("installed")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]), "install", partition="default" if partitions else None
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the staged file is the one that was staged last
        assert Path(stage_dir, "foo").read_text() == "installed", (
            "Expected staging to allow overwriting of already-staged files"
        )

    def test_migrate_files_supports_no_follow_symlinks(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        install_dir.mkdir()
        stage_dir.mkdir()

        Path(install_dir, "foo").write_text("installed")
        Path(install_dir, "bar").symlink_to("foo")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]), "install", partition="default" if partitions else None
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files,
            dirs=dirs,
            srcdir=install_dir,
            destdir=stage_dir,
            follow_symlinks=False,
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlink was preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to still be a symlink."
        )

        assert os.readlink(os.path.join(stage_dir, "bar")) == "foo", (
            "Expected migrated 'bar' to point to 'foo'"
        )

    def test_migrate_files_preserves_symlink_file(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        install_dir.mkdir()
        stage_dir.mkdir()

        Path(install_dir, "foo").write_text("installed")
        Path(install_dir, "bar").symlink_to("foo")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]), "install", partition="default" if partitions else None
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to be a symlink."
        )

    def test_migrate_files_no_follow_symlinks(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")
        bin_path = Path("bin")
        partition = "default" if partitions else None

        Path(install_dir, "usr/bin").mkdir(parents=True)
        stage_dir.mkdir()

        Path(install_dir, "usr/bin/foo").write_text("installed")
        Path("install", bin_path).symlink_to("usr/bin")

        files, dirs = filesets.migratable_filesets(
            Fileset(["-usr"]), "install", partition
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert files == {"bin"}
        assert dirs == set()
        assert Path(stage_dir, bin_path).is_symlink()

    def test_migrate_files_preserves_symlink_nested_file(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        Path(install_dir, "a").mkdir(parents=True)
        stage_dir.mkdir()

        Path(install_dir, "a/foo").write_text("installed")
        Path(install_dir, "a/bar").symlink_to("foo")
        Path(install_dir, "bar").symlink_to("a/foo")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]),
            "install",
            partition="default" if partitions else None,
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to be a symlink."
        )
        assert Path(stage_dir, "a/bar").is_symlink(), (
            "Expected migrated 'a/bar' to be a symlink."
        )

    def test_migrate_files_preserves_symlink_empty_dir(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        Path(install_dir, "foo").mkdir(parents=True)
        stage_dir.mkdir()

        Path(install_dir, "bar").symlink_to("foo")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]),
            "install",
            partition="default" if partitions else None,
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to be a symlink."
        )

    def test_migrate_files_preserves_symlink_nonempty_dir(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        Path(install_dir, "foo").mkdir(parents=True)
        stage_dir.mkdir()

        Path(install_dir, "bar").symlink_to("foo")

        Path(install_dir, "foo/xfile").write_text("installed")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]),
            "install",
            partition="default" if partitions else None,
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to be a symlink."
        )

    def test_migrate_files_preserves_symlink_nested_dir(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        Path(install_dir, "a/b").mkdir(parents=True)
        stage_dir.mkdir()

        Path(install_dir, "bar").symlink_to("a/b")
        Path(install_dir, "a/bar").symlink_to("b")

        Path(install_dir, "a/b/xfile").write_text("installed")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]), "install", partition="default" if partitions else None
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files, dirs=dirs, srcdir=install_dir, destdir=stage_dir
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlinks were preserved
        assert Path(stage_dir, "bar").is_symlink(), (
            "Expected migrated 'bar' to be a symlink."
        )

        assert os.path.islink(os.path.join("stage", "a", "bar")), (
            "Expected migrated 'a/bar' to be a symlink."
        )

    def test_migrate_files_supports_follow_symlinks(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        install_dir.mkdir()
        stage_dir.mkdir()

        Path(install_dir, "foo").write_text("installed")
        Path(install_dir, "bar").symlink_to("foo")

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]), "install", partition="default" if partitions else None
        )
        migrated_files, migrated_dirs = migration.migrate_files(
            files=files,
            dirs=dirs,
            srcdir=install_dir,
            destdir=stage_dir,
            follow_symlinks=True,
        )

        # Ensure all files were migrated
        assert migrated_files == files
        assert migrated_dirs == dirs

        # Verify that the symlink was preserved
        assert Path(stage_dir, "bar").is_symlink() is False, (
            "Expected migrated 'bar' to no longer be a symlink."
        )
        assert Path(stage_dir, "bar").read_text() == "installed", (
            "Expected migrated 'bar' to be a copy of 'foo'"
        )

    def test_migrate_files_preserves_file_mode(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        install_dir.mkdir()
        stage_dir.mkdir()

        filepath = Path(install_dir, "foo")
        filepath.write_text("installed")

        mode = filepath.stat().st_mode

        new_mode = 0o777
        filepath.chmod(new_mode)
        assert mode != new_mode

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]),
            "install",
            partition="default" if partitions else None,
        )
        migration.migrate_files(
            files=files,
            dirs=dirs,
            srcdir=install_dir,
            destdir=stage_dir,
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(Path(stage_dir, "foo").stat().st_mode)

    # TODO: add test_migrate_files_preserves_file_mode_chown_permissions

    def test_migrate_files_preserves_directory_mode(self, partitions):
        install_dir = Path("install")
        stage_dir = Path("stage")

        Path(install_dir, "foo").mkdir(parents=True)
        stage_dir.mkdir()

        filepath = Path(install_dir, "foo", "bar")
        filepath.write_text("installed")

        mode = filepath.stat().st_mode

        new_mode = 0o777
        assert mode != new_mode
        filepath.parent.chmod(new_mode)
        filepath.chmod(new_mode)

        files, dirs = filesets.migratable_filesets(
            Fileset(["*"]),
            "install",
            partition="default" if partitions else None,
        )
        migration.migrate_files(
            files=files,
            dirs=dirs,
            srcdir=install_dir,
            destdir=stage_dir,
            follow_symlinks=True,
        )

        assert new_mode == stat.S_IMODE(Path(stage_dir, "foo").stat().st_mode)
        assert new_mode == stat.S_IMODE(Path(stage_dir, "foo/bar").stat().st_mode)

    def test_migration_with_permissions(self, mock_chown):
        source = Path("source")
        source.mkdir()

        (source / "1.txt").touch()
        (source / "bar").mkdir()
        (source / "bar/2.txt").touch()
        (source / "baz").mkdir()
        (source / "baz/3.txt").touch()
        (source / "baz/qux").mkdir()
        (source / "baz/qux/4.txt").touch()

        os.chmod(source / "1.txt", 0o644)
        os.chmod(source / "bar/2.txt", 0o555)

        target = Path("target")
        target.mkdir()

        permissions = [
            Permissions(path="1.txt", mode="755"),
            Permissions(path="bar/*", mode="444"),
            Permissions(path="baz/*", owner=1111, group=2222),
        ]

        migration.migrate_files(
            files={"1.txt", "bar/2.txt", "baz/3.txt", "baz/qux/4.txt"},
            dirs={"bar", "baz", "baz/qux"},
            srcdir=source,
            destdir=target,
            permissions=permissions,
        )

        assert stat.S_IMODE(os.stat(target / "1.txt").st_mode) == 0o755
        assert stat.S_IMODE(os.stat(target / "bar/2.txt").st_mode) == 0o444

        paths_with_chown = [
            "target/baz/3.txt",
            "target/baz/qux",
            "target/baz/qux/4.txt",
        ]
        for p in paths_with_chown:
            call = mock_chown[p]
            assert call.owner == 1111
            assert call.group == 2222


@pytest.mark.usefixtures("new_dir")
class TestFileMigrationErrors:
    def test_migratable_filesets_partition_defined_error(self):
        """Error if the partition feature is disabled and a partition is provided."""
        with pytest.raises(errors.FeatureError) as raised:
            filesets.migratable_filesets(Fileset(["*"]), "install", partition="default")

        assert features.Features().enable_partitions is False
        assert (
            "The partition feature must be enabled if a partition is provided."
        ) in str(raised.value)


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify helper functions."""

    def test_clean_shared_area(self, new_dir, partitions):
        p1 = Part("p1", {"plugin": "dump", "source": "subdir1"}, partitions=partitions)
        Path("subdir1").mkdir()
        Path("subdir1/foo.txt").write_text("content")

        p2 = Part("p2", {"plugin": "dump", "source": "subdir2"}, partitions=partitions)
        Path("subdir2").mkdir()
        Path("subdir2/foo.txt").write_text("content")
        Path("subdir2/bar.txt").write_text("other content")
        Path("subdir2/baz.txt").write_text("yet another content")

        foo_path = Path("stage/foo.txt")
        bar_path = Path("stage/bar.txt")

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1, p2], base_layer_dir=None
        )

        handler1 = part_handler.PartHandler(
            p1,
            part_info=PartInfo(info, part=p1),
            part_list=[p1, p2],
            overlay_manager=ovmgr,
        )
        handler2 = part_handler.PartHandler(
            p2,
            part_info=PartInfo(info, part=p2),
            part_list=[p1, p2],
            overlay_manager=ovmgr,
        )

        for step in [Step.PULL, Step.BUILD, Step.STAGE]:
            handler1.run_action(Action("p1", step))
            handler2.run_action(Action("p2", step))

        part_states = part_handler._load_part_states(Step.STAGE, part_list=[p1, p2])

        assert foo_path.is_file()
        assert bar_path.is_file()

        # TODO: also test files shared with overlay
        for partition in partitions or (None,):
            migration.clean_shared_area(
                part_name="p1",
                shared_dir=p1.stage_dir,
                part_states=part_states,
                overlay_migration_state=None,
                partition=partition,
            )

        assert foo_path.is_file()  # remains, it's shared with p2
        assert bar_path.is_file()

        for partition in partitions or (None,):
            migration.clean_shared_area(
                part_name="p2",
                shared_dir=p2.stage_dir,
                part_states=part_states,
                overlay_migration_state=None,
                partition=partition,
            )

        assert not foo_path.exists()
        assert not bar_path.exists()

    def test_clean_migrated_files(self, new_dir, partitions):
        Path("subdir").mkdir()
        Path("subdir/foo.txt").touch()
        Path("subdir/bar").mkdir()

        stage = Path(new_dir / "stage")
        foo_path = stage / "foo.txt"
        bar_path = stage / "bar"

        p1 = Part("p1", {"plugin": "dump", "source": "subdir"}, partitions=partitions)
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, part=p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = part_handler.PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        assert foo_path.is_file()
        assert bar_path.is_dir()

        migration._clean_migrated_files({"foo.txt"}, {"bar"}, stage)

        assert not foo_path.exists()
        assert not bar_path.exists()

    def test_clean_migrated_files_missing(self, new_dir, partitions):
        Path("subdir").mkdir()

        p1 = Part("p1", {"plugin": "dump", "source": "subdir"}, partitions=partitions)
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, part=p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = part_handler.PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler.run_action(Action("p1", Step.PULL))
        handler.run_action(Action("p1", Step.BUILD))
        handler.run_action(Action("p1", Step.STAGE))

        # this shouldn't raise an exception
        migration._clean_migrated_files({"foo.txt"}, {"bar"}, Path("stage"))


class TestFilterWhiteouts:
    """Remove dangling file and opaque dir whiteouts."""

    def test_file_whiteout_removal(self, new_dir):
        """Expect all whiteout files to be removed."""
        files = {
            "f1",
            "f2",
            "f3",
            ".wh.foo.txt",
            "a/.wh.bar.txt",
            "a/.wh.bar2.txt",
            "b/baz.txt",
            "b/.wh..wh..opq",
        }
        dirs = {"a", "b", "c"}

        # Create a backing file and dir
        Path("foo.txt").touch()
        Path("a").mkdir()
        Path("a/bar.txt").touch()
        Path("b").mkdir()

        migration.filter_dangling_whiteouts(files, dirs, base_dir=new_dir)

        # expect no modification in files or dirs
        assert files == {
            "f1",
            "f2",
            "f3",
            ".wh.foo.txt",  # backing file exists
            "a/.wh.bar.txt",  # backing file exists
            "b/baz.txt",
            "b/.wh..wh..opq",  # backing dir exists
        }
        assert dirs == {"a", "b", "c"}

    def test_file_whiteout_removal_no_base(self):
        """Ignore whiteout files if no base set."""
        files = {
            "f1",
            "f2",
            "f3",
            ".wh.foo.txt",
            "a/.wh.bar.txt",
            "b/baz.txt",
            "b/.wh..wh..opq",
        }
        dirs = {"a", "b", "c"}

        migration.filter_dangling_whiteouts(files, dirs, base_dir=None)

        # expect no modification in files or dirs
        assert files == {
            "f1",
            "f2",
            "f3",
            ".wh.foo.txt",
            "a/.wh.bar.txt",
            "b/baz.txt",
            "b/.wh..wh..opq",
        }
        assert dirs == {"a", "b", "c"}
