# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021,2024 Canonical Ltd.
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
import shutil
from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.sources import errors as sources_errors
from craft_parts.sources import sources
from craft_parts.sources.local_source import LocalSource


class TestLocal:
    """Various tests for the local source handler."""

    def test_pull_with_existing_empty_source_dir_creates_hardlinks(
        self, new_dir, partitions
    ):
        src_path = Path("src", "dir")
        src_path.mkdir(parents=True)
        (src_path / "file").open("w").close()

        dest_path = Path("destination")
        dest_path.mkdir()

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert dest_path.is_symlink() is False
        assert (dest_path / "dir").is_symlink() is False
        assert (dest_path / "dir" / "file").stat().st_nlink > 1

    def test_pull_with_existing_source_tree_creates_hardlinks(
        self, new_dir, partitions
    ):
        src_path = Path("src", "dir")
        src_path.mkdir(parents=True)
        (src_path / "file").open("w").close()

        dest_path = Path("destination")
        dest_path.mkdir()
        (dest_path / "existing-file").open("w").close()

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink. Also verify that existing-file still exists.
        assert dest_path.is_symlink() is False
        assert (dest_path / "dir").is_symlink() is False
        assert (dest_path / "existing-file").is_file()
        assert (dest_path / "dir" / "file").stat().st_nlink > 1

    def test_pull_with_existing_source_link_error(self, new_dir, partitions):
        src_path = Path("src", "dir")
        src_path.mkdir(parents=True)
        (src_path / "file").open("w").close()

        # Note that this is a symlink now instead of a directory
        Path("destination").symlink_to("dummy")

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)

        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pull_with_existing_source_file_error(self, new_dir, partitions):
        src_path = Path("src", "dir")
        src_path.mkdir(parents=True)
        (src_path / "file").open("w").close()

        # Note that this is a file now instead of a directory
        Path("destination").open("w").close()

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pulling_twice_with_existing_source_dir_recreates_hardlinks(
        self, new_dir, partitions
    ):
        src_path = Path("src", "dir")
        src_path.mkdir(parents=True)
        (src_path / "file").open("w").close()

        dest_path = Path("destination")
        dest_path.mkdir()

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert dest_path.is_symlink() is False
        assert (dest_path / "dir").is_symlink() is False
        assert (dest_path / "dir" / "file").stat().st_nlink > 1

    def test_pull_ignores_own_work_data(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        Path("parts/foo/src").mkdir(parents=True)
        Path("stage").mkdir(parents=True)
        Path("prime").mkdir(parents=True)
        Path("other").mkdir(parents=True)
        if partitions:
            Path("partitions").mkdir(parents=True)

        # Create an application-specific file
        Path("foo.znap").open("w").close()

        # Now make some real files
        Path("dir").mkdir(parents=True)
        Path("dir", "file").open("w").close()

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(
            ".",
            "parts/foo/src",
            cache_dir=new_dir,
            ignore_patterns=["*.znap"],
            project_dirs=dirs,
        )
        local.pull()

        # Verify that the work directories got filtered out
        assert Path("parts", "foo", "src", "parts").is_dir() is False
        assert Path("parts", "foo", "src", "stage").is_dir() is False
        assert Path("parts", "foo", "src", "prime").is_dir() is False
        assert Path("parts", "foo", "src", "partitions").is_dir() is False
        assert Path("parts", "foo", "src", "other").is_dir()
        assert Path("parts", "foo", "src", "foo.znap").is_file() is False

        # Verify that the real stuff made it in.
        assert Path("parts", "foo", "src", "dir").is_dir()
        assert Path("parts", "foo", "src", "dir", "file").stat().st_nlink > 1

    def test_pull_ignores_own_work_data_work_dir(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        Path("src", "work_dir").mkdir(parents=True)
        Path("src", "parts").mkdir(parents=True)
        Path("src", "stage").mkdir(parents=True)
        Path("src", "prime").mkdir(parents=True)
        Path("src", "other").mkdir(parents=True)
        if partitions:
            Path("src", "partitions").mkdir(parents=True)
        Path("src", "foo.znap").open("w").close()

        Path("destination").mkdir()

        dirs = ProjectDirs(work_dir="src/work_dir", partitions=partitions)
        local = LocalSource(
            "src",
            "destination",
            cache_dir=new_dir,
            project_dirs=dirs,
            ignore_patterns=["*.znap"],
        )
        local.pull()

        # Verify that the work directories got filtered out
        assert Path("destination", "work_dir").is_dir() is False
        assert Path("destination", "foo.znap").is_dir() is False
        assert Path("destination", "other").is_dir()

        # These are now allowed since we have set work_dir
        assert Path("destination", "parts").is_dir()
        assert Path("destination", "stage").is_dir()
        assert Path("destination", "prime").is_dir()
        if partitions:
            assert Path("destination", "partitions").is_dir()

    def test_pull_ignores_own_work_data_deep_work_dir(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        Path("src", "some/deep/work_dir").mkdir(parents=True)
        Path("src", "parts").mkdir(parents=True)
        Path("src", "stage").mkdir(parents=True)
        Path("src", "prime").mkdir(parents=True)
        Path("src", "other").mkdir(parents=True)
        Path("src", "work_dir").mkdir(parents=True)
        if partitions:
            Path("src", "partitions").mkdir(parents=True)
        Path("src", "foo.znap").open("w").close()

        Path("destination").mkdir()

        dirs = ProjectDirs(work_dir="src/some/deep/work_dir", partitions=partitions)
        local = LocalSource(
            "src",
            "destination",
            cache_dir=new_dir,
            project_dirs=dirs,
            ignore_patterns=["*.znap"],
        )
        local.pull()

        # Verify that the work directories got filtered out
        assert Path("destination", "some/deep/work_dir").is_dir() is False
        assert Path("destination", "foo.znap").is_dir() is False
        assert Path("destination", "other").is_dir()

        # These are now allowed since we have set work_dir
        assert Path("destination", "parts").is_dir()
        assert Path("destination", "stage").is_dir()
        assert Path("destination", "prime").is_dir()
        if partitions:
            assert Path("destination", "partitions").is_dir()

        # This has the same name but it's not the real work dir
        assert Path("destination", "work_dir").is_dir()

    def test_pull_work_dir_outside(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        Path("src", "work_dir").mkdir(parents=True)
        Path("src", "parts").mkdir(parents=True)
        Path("src", "stage").mkdir(parents=True)
        Path("src", "prime").mkdir(parents=True)
        Path("src", "other").mkdir(parents=True)
        if partitions:
            Path("src", "partitions").mkdir(parents=True)

        Path("destination").mkdir()

        dirs = ProjectDirs(work_dir="/work_dir", partitions=partitions)
        local = LocalSource(
            "src",
            "destination",
            cache_dir=new_dir,
            project_dirs=dirs,
            ignore_patterns=["*.znap"],
        )
        local.pull()

        # These are all allowed since work_dir is located outside
        assert Path("destination", "work_dir").is_dir()
        assert Path("destination", "other").is_dir()
        assert Path("destination", "parts").is_dir()
        assert Path("destination", "stage").is_dir()
        assert Path("destination", "prime").is_dir()
        if partitions:
            assert Path("destination", "partitions").is_dir()

    def test_pull_keeps_symlinks(self, new_dir, partitions):
        # Create a source containing a directory, a file and symlinks to both.
        Path("src", "dir").mkdir(parents=True)
        Path("src", "dir", "file").open("w").close()
        Path("src", "dir_symlink").symlink_to(Path("dir"))
        Path("src", "dir", "file_symlink").symlink_to(Path("file"))

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that both the file and the directory symlinks were kept.
        assert Path("destination", "dir").is_dir()
        dir_symlink = Path("destination", "dir_symlink")
        assert dir_symlink.is_symlink()
        assert dir_symlink.readlink() == Path("dir")
        assert Path("destination", "dir", "file").is_file()
        file_symlink = Path("destination", "dir", "file_symlink")
        assert file_symlink.is_symlink()
        assert file_symlink.readlink() == Path("file")

    def test_has_source_handler_entry(self):
        assert sources._get_source_handler_class("", source_type="local") is LocalSource

    def test_ignore_patterns_workdir(self, new_dir, partitions):
        ignore_patterns = ["hello"]
        project_dirs = ProjectDirs(work_dir=Path("src/work"), partitions=partitions)

        s1 = LocalSource(
            "src",
            "destination",
            project_dirs=project_dirs,
            cache_dir=new_dir,
            ignore_patterns=ignore_patterns,
        )
        assert s1._ignore_patterns == ["hello", "work"]

        s2 = LocalSource(
            "src",
            "destination",
            project_dirs=project_dirs,
            cache_dir=new_dir,
            ignore_patterns=ignore_patterns,
        )
        assert s2._ignore_patterns == ["hello", "work"]

    def test_source_does_not_exist(self, new_dir, partitions):
        dirs = ProjectDirs(work_dir=Path("src/work"), partitions=partitions)
        local = LocalSource(
            "does-not-exist",
            "destination",
            cache_dir=new_dir,
            project_dirs=dirs,
        )

        with pytest.raises(sources_errors.SourceNotFound):
            local.pull()


class TestLocalUpdate:
    """Verify that the local source can detect changes and update."""

    @pytest.mark.parametrize(
        ("name", "ignored"),
        [
            ("file", False),
            ("file.ignore", True),
        ],
    )
    def test_file_modified(self, new_dir, partitions, name, ignored):
        source = Path("source")
        destination = Path("destination")
        source.mkdir()
        destination.mkdir()

        with Path(source, name).open("w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(Path(source, name), "reference")
        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime("reference", (access_time, modify_time + 1))

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(
            source,
            destination,
            cache_dir=new_dir,
            ignore_patterns=["*.ignore"],
            project_dirs=dirs,
        )
        local.pull()

        # Update check on non-existent files should return False
        assert local.check_if_outdated("invalid") is False

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        if ignored:
            assert Path(destination, name).exists() is False
        else:
            with Path(destination, name).open() as f:
                assert f.read() == "1"

        # Now update the file in source, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with Path(source, name).open("w") as f:
            f.write("2")

        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime(Path(source, name), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference") is not ignored

        local.update()

        if ignored:
            assert Path(destination, name).exists() is False
        else:
            with Path(destination, name).open() as f:
                assert f.read() == "2"

    def test_file_added(self, new_dir, partitions):
        source = Path("source")
        destination = Path("destination")
        source.mkdir()
        destination.mkdir()

        with Path(source, "file1").open("w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(Path(source, "file1"), "reference")
        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime("reference", (access_time, modify_time + 1))

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(source, destination, cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert Path(destination, "file1").is_file()

        # Now add a new file, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with Path(source, "file2").open("w") as f:
            f.write("2")

        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime(Path(source, "file2"), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert Path(destination, "file2").is_file()

    def test_directory_modified(self, new_dir, partitions):
        source = Path("source")
        source_dir = source / "dir"
        destination = Path("destination")
        source_dir.mkdir(parents=True)
        destination.mkdir()

        with Path(source_dir, "file1").open("w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(Path(source_dir, "file1"), "reference")
        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime("reference", (access_time, modify_time + 1))
        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(source, destination, cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert Path(destination, "dir", "file1").is_file()

        # Now add a new file to the directory, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with Path(source_dir, "file2").open("w") as f:
            f.write("2")

        access_time = Path("reference").stat().st_atime
        modify_time = Path("reference").stat().st_mtime
        os.utime(Path(source_dir, "file2"), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert Path(destination, "dir", "file2").is_file()

    def test_ignored_files(self, new_dir, partitions):
        Path("source").mkdir()
        Path("destination").mkdir()
        Path("source/foo.txt").touch()
        Path("reference").touch()

        ignore_patterns = ["*.ignore"]
        also_ignore = ["also ignore"]

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(
            "source",
            "destination",
            cache_dir=new_dir,
            ignore_patterns=ignore_patterns,
            project_dirs=dirs,
        )
        local.pull()

        # Add a file to ignore, existing patterns must not change.
        local.check_if_outdated("reference", ignore_files=also_ignore)
        assert also_ignore == ["also ignore"]
        assert local._ignore_patterns == ["*.ignore"]
