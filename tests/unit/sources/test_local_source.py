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
import pathlib
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
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123

        os.mkdir("destination")  # noqa: PTH102

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert os.path.islink("destination") is False  # noqa: PTH114
        assert os.path.islink(os.path.join("destination", "dir")) is False  # noqa: PTH114, PTH118
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1  # noqa: PTH116, PTH118

    def test_pull_with_existing_source_tree_creates_hardlinks(
        self, new_dir, partitions
    ):
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123

        os.mkdir("destination")  # noqa: PTH102
        open(os.path.join("destination", "existing-file"), "w").close()  # noqa: PTH118, PTH123

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink. Also verify that existing-file still exists.
        assert os.path.islink("destination") is False  # noqa: PTH114
        assert os.path.islink(os.path.join("destination", "dir")) is False  # noqa: PTH114, PTH118
        assert os.path.isfile(os.path.join("destination", "existing-file"))  # noqa: PTH113, PTH118
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1  # noqa: PTH116, PTH118

    def test_pull_with_existing_source_link_error(self, new_dir, partitions):
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123

        # Note that this is a symlink now instead of a directory
        pathlib.Path("destination").symlink_to("dummy")

        dirs = ProjectDirs(partitions=partitions)
        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)

        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pull_with_existing_source_file_error(self, new_dir, partitions):
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123

        # Note that this is a file now instead of a directory
        open("destination", "w").close()  # noqa: PTH123

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pulling_twice_with_existing_source_dir_recreates_hardlinks(
        self, new_dir, partitions
    ):
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123

        os.mkdir("destination")  # noqa: PTH102

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert os.path.islink("destination") is False  # noqa: PTH114
        assert os.path.islink(os.path.join("destination", "dir")) is False  # noqa: PTH114, PTH118
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1  # noqa: PTH116, PTH118

    def test_pull_ignores_own_work_data(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        os.makedirs("parts/foo/src")  # noqa: PTH103
        os.makedirs("stage")  # noqa: PTH103
        os.makedirs("prime")  # noqa: PTH103
        os.makedirs("other")  # noqa: PTH103
        if partitions:
            os.makedirs("partitions")  # noqa: PTH103

        # Create an application-specific file
        open("foo.znap", "w").close()  # noqa: PTH123

        # Now make some real files
        os.makedirs("dir")  # noqa: PTH103
        open(os.path.join("dir", "file"), "w").close()  # noqa: PTH118, PTH123

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
        assert os.path.isdir(os.path.join("parts", "foo", "src", "parts")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("parts", "foo", "src", "stage")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("parts", "foo", "src", "prime")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("parts", "foo", "src", "partitions")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("parts", "foo", "src", "other"))  # noqa: PTH112, PTH118
        assert os.path.isfile(os.path.join("parts", "foo", "src", "foo.znap")) is False  # noqa: PTH113, PTH118

        # Verify that the real stuff made it in.
        assert os.path.isdir(os.path.join("parts", "foo", "src", "dir"))  # noqa: PTH112, PTH118
        assert os.stat(os.path.join("parts", "foo", "src", "dir", "file")).st_nlink > 1  # noqa: PTH116, PTH118

    def test_pull_ignores_own_work_data_work_dir(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        os.makedirs(os.path.join("src", "work_dir"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "parts"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "stage"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "prime"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "other"))  # noqa: PTH103, PTH118
        if partitions:
            os.makedirs(os.path.join("src", "partitions"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "foo.znap"), "w").close()  # noqa: PTH118, PTH123

        os.mkdir("destination")  # noqa: PTH102

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
        assert os.path.isdir(os.path.join("destination", "work_dir")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "foo.znap")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "other"))  # noqa: PTH112, PTH118

        # These are now allowed since we have set work_dir
        assert os.path.isdir(os.path.join("destination", "parts"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "stage"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "prime"))  # noqa: PTH112, PTH118
        if partitions:
            assert os.path.isdir(os.path.join("destination", "partitions"))  # noqa: PTH112, PTH118

    def test_pull_ignores_own_work_data_deep_work_dir(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        os.makedirs(os.path.join("src", "some/deep/work_dir"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "parts"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "stage"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "prime"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "other"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "work_dir"))  # noqa: PTH103, PTH118
        if partitions:
            os.makedirs(os.path.join("src", "partitions"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "foo.znap"), "w").close()  # noqa: PTH118, PTH123

        os.mkdir("destination")  # noqa: PTH102

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
        assert os.path.isdir(os.path.join("destination", "some/deep/work_dir")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "foo.znap")) is False  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "other"))  # noqa: PTH112, PTH118

        # These are now allowed since we have set work_dir
        assert os.path.isdir(os.path.join("destination", "parts"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "stage"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "prime"))  # noqa: PTH112, PTH118
        if partitions:
            assert os.path.isdir(os.path.join("destination", "partitions"))  # noqa: PTH112, PTH118

        # This has the same name but it's not the real work dir
        assert os.path.isdir(os.path.join("destination", "work_dir"))  # noqa: PTH112, PTH118

    def test_pull_work_dir_outside(self, new_dir, partitions):
        # Make the snapcraft-specific directories
        os.makedirs(os.path.join("src", "work_dir"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "parts"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "stage"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "prime"))  # noqa: PTH103, PTH118
        os.makedirs(os.path.join("src", "other"))  # noqa: PTH103, PTH118
        if partitions:
            os.makedirs(os.path.join("src", "partitions"))  # noqa: PTH103, PTH118

        os.mkdir("destination")  # noqa: PTH102

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
        assert os.path.isdir(os.path.join("destination", "work_dir"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "other"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "parts"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "stage"))  # noqa: PTH112, PTH118
        assert os.path.isdir(os.path.join("destination", "prime"))  # noqa: PTH112, PTH118
        if partitions:
            assert os.path.isdir(os.path.join("destination", "partitions"))  # noqa: PTH112, PTH118

    def test_pull_keeps_symlinks(self, new_dir, partitions):
        # Create a source containing a directory, a file and symlinks to both.
        os.makedirs(os.path.join("src", "dir"))  # noqa: PTH103, PTH118
        open(os.path.join("src", "dir", "file"), "w").close()  # noqa: PTH118, PTH123
        pathlib.Path("src", "dir_symlink").symlink_to("dir")
        pathlib.Path("src", "dir", "file_symlink").symlink_to("file")

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource("src", "destination", cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Verify that both the file and the directory symlinks were kept.
        assert os.path.isdir(os.path.join("destination", "dir"))  # noqa: PTH112, PTH118
        dir_symlink = os.path.join("destination", "dir_symlink")  # noqa: PTH118
        assert os.path.islink(dir_symlink)  # noqa: PTH114
        assert os.readlink(dir_symlink) == "dir"  # noqa: PTH115
        assert os.path.isfile(os.path.join("destination", "dir", "file"))  # noqa: PTH113, PTH118
        file_symlink = os.path.join("destination", "dir", "file_symlink")  # noqa: PTH118
        assert os.path.islink(file_symlink)  # noqa: PTH114
        assert os.readlink(file_symlink) == "file"  # noqa: PTH115

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
        source = "source"
        destination = "destination"
        os.mkdir(source)  # noqa: PTH102
        os.mkdir(destination)  # noqa: PTH102

        with open(os.path.join(source, name), "w") as f:  # noqa: PTH118, PTH123
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source, name), "reference")  # noqa: PTH118
        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
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
            assert os.path.exists(os.path.join(destination, name)) is False  # noqa: PTH110, PTH118
        else:
            with open(os.path.join(destination, name)) as f:  # noqa: PTH118, PTH123
                assert f.read() == "1"

        # Now update the file in source, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source, name), "w") as f:  # noqa: PTH118, PTH123
            f.write("2")

        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
        os.utime(os.path.join(source, name), (access_time, modify_time + 1))  # noqa: PTH118

        # Expect update to be available
        assert local.check_if_outdated("reference") is not ignored

        local.update()

        if ignored:
            assert os.path.exists(os.path.join(destination, name)) is False  # noqa: PTH110, PTH118
        else:
            with open(os.path.join(destination, name)) as f:  # noqa: PTH118, PTH123
                assert f.read() == "2"

    def test_file_added(self, new_dir, partitions):
        source = "source"
        destination = "destination"
        os.mkdir(source)  # noqa: PTH102
        os.mkdir(destination)  # noqa: PTH102

        with open(os.path.join(source, "file1"), "w") as f:  # noqa: PTH118, PTH123
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source, "file1"), "reference")  # noqa: PTH118
        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
        os.utime("reference", (access_time, modify_time + 1))

        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(source, destination, cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert os.path.isfile(os.path.join(destination, "file1"))  # noqa: PTH113, PTH118

        # Now add a new file, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source, "file2"), "w") as f:  # noqa: PTH118, PTH123
            f.write("2")

        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
        os.utime(os.path.join(source, "file2"), (access_time, modify_time + 1))  # noqa: PTH118

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert os.path.isfile(os.path.join(destination, "file2"))  # noqa: PTH113, PTH118

    def test_directory_modified(self, new_dir, partitions):
        source = "source"
        source_dir = os.path.join(source, "dir")  # noqa: PTH118
        destination = "destination"
        os.makedirs(source_dir)  # noqa: PTH103
        os.mkdir(destination)  # noqa: PTH102

        with open(os.path.join(source_dir, "file1"), "w") as f:  # noqa: PTH118, PTH123
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source_dir, "file1"), "reference")  # noqa: PTH118
        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
        os.utime("reference", (access_time, modify_time + 1))
        dirs = ProjectDirs(partitions=partitions)

        local = LocalSource(source, destination, cache_dir=new_dir, project_dirs=dirs)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert os.path.isfile(os.path.join(destination, "dir", "file1"))  # noqa: PTH113, PTH118

        # Now add a new file to the directory, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source_dir, "file2"), "w") as f:  # noqa: PTH118, PTH123
            f.write("2")

        access_time = os.stat("reference").st_atime  # noqa: PTH116
        modify_time = os.stat("reference").st_mtime  # noqa: PTH116
        os.utime(os.path.join(source_dir, "file2"), (access_time, modify_time + 1))  # noqa: PTH118

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert os.path.isfile(os.path.join(destination, "dir", "file2"))  # noqa: PTH113, PTH118

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
