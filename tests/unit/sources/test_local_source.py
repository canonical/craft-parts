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
import shutil

import pytest

from craft_parts import errors
from craft_parts.sources import sources
from craft_parts.sources.local_source import LocalSource


class TestLocal:
    """Various tests for the local source handler."""

    def test_pull_with_existing_empty_source_dir_creates_hardlinks(self, new_dir):
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        os.mkdir("destination")

        local = LocalSource("src", "destination", cache_dir=new_dir)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert os.path.islink("destination") is False
        assert os.path.islink(os.path.join("destination", "dir")) is False
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1

    def test_pull_with_existing_source_tree_creates_hardlinks(self, new_dir):
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        os.mkdir("destination")
        open(os.path.join("destination", "existing-file"), "w").close()

        local = LocalSource("src", "destination", cache_dir=new_dir)
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink. Also verify that existing-file still exists.
        assert os.path.islink("destination") is False
        assert os.path.islink(os.path.join("destination", "dir")) is False
        assert os.path.isfile(os.path.join("destination", "existing-file"))
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1

    def test_pull_with_existing_source_link_error(self, new_dir):
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        # Note that this is a symlink now instead of a directory
        os.symlink("dummy", "destination")

        local = LocalSource("src", "destination", cache_dir=new_dir)

        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pull_with_existing_source_file_error(self, new_dir):
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        # Note that this is a file now instead of a directory
        open("destination", "w").close()

        local = LocalSource("src", "destination", cache_dir=new_dir)
        with pytest.raises(errors.CopyTreeError):
            local.pull()

    def test_pulling_twice_with_existing_source_dir_recreates_hardlinks(self, new_dir):
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        os.mkdir("destination")

        local = LocalSource("src", "destination", cache_dir=new_dir)
        local.pull()
        local.pull()

        # Verify that the directories are not symlinks, but the file is a
        # hardlink.
        assert os.path.islink("destination") is False
        assert os.path.islink(os.path.join("destination", "dir")) is False
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1

    def test_pull_ignores_own_work_data(self, new_dir):
        # Make the snapcraft-specific directories
        os.makedirs(os.path.join("src", "parts"))
        os.makedirs(os.path.join("src", "stage"))
        os.makedirs(os.path.join("src", "prime"))
        os.makedirs(os.path.join("src", ".snapcraft"))
        os.makedirs(os.path.join("src", "snap"))

        # Make the snapcraft.yaml (and hidden one) and a built snap
        open(os.path.join("src", "snapcraft.yaml"), "w").close()
        open(os.path.join("src", ".snapcraft.yaml"), "w").close()
        open(os.path.join("src", "foo.snap"), "w").close()

        # Make the global state cache
        open(os.path.join("src", ".snapcraft", "state"), "w").close()

        # Now make some real files
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()

        os.mkdir("destination")

        local = LocalSource("src", "destination", cache_dir=new_dir)
        local.pull()

        # Verify that the snapcraft-specific stuff got filtered out
        assert os.path.isdir(os.path.join("destination", "parts")) is False
        assert os.path.isdir(os.path.join("destination", "stage")) is False
        assert os.path.isdir(os.path.join("destination", "prime")) is False

        assert os.path.isdir(os.path.join("destination", "snap"))
        assert os.path.isfile(os.path.join("destination", ".snapcraft.yaml"))
        assert os.path.isfile(os.path.join("destination", "snapcraft.yaml"))

        assert os.path.isfile(os.path.join("destination", "foo.snap")) is False

        # Verify that the real stuff made it in.
        assert os.path.islink("destination") is False
        assert os.path.islink(os.path.join("destination", "dir")) is False
        assert os.stat(os.path.join("destination", "dir", "file")).st_nlink > 1

    def test_pull_keeps_symlinks(self, new_dir):
        # Create a source containing a directory, a file and symlinks to both.
        os.makedirs(os.path.join("src", "dir"))
        open(os.path.join("src", "dir", "file"), "w").close()
        os.symlink("dir", os.path.join("src", "dir_symlink"))
        os.symlink("file", os.path.join("src", "dir", "file_symlink"))

        local = LocalSource("src", "destination", cache_dir=new_dir)
        local.pull()

        # Verify that both the file and the directory symlinks were kept.
        assert os.path.isdir(os.path.join("destination", "dir"))
        dir_symlink = os.path.join("destination", "dir_symlink")
        assert os.path.islink(dir_symlink) and os.readlink(dir_symlink) == "dir"
        assert os.path.isfile(os.path.join("destination", "dir", "file"))
        file_symlink = os.path.join("destination", "dir", "file_symlink")
        assert os.path.islink(file_symlink) and os.readlink(file_symlink) == "file"

    def test_has_source_handler_entry(self):
        assert sources._source_handler["local"] is LocalSource


class TestLocalUpdate:
    """Verify that the local source can detect changes and update."""

    def test_file_modified(self, new_dir):
        source = "source"
        destination = "destination"
        os.mkdir(source)
        os.mkdir(destination)

        with open(os.path.join(source, "file"), "w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source, "file"), "reference")
        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime("reference", (access_time, modify_time + 1))

        local = LocalSource(source, destination, cache_dir=new_dir)
        local.pull()

        # Update check on non-existent files should return False
        assert local.check_if_outdated("invalid") is False

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        with open(os.path.join(destination, "file")) as f:
            assert f.read() == "1"

        # Now update the file in source, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source, "file"), "w") as f:
            f.write("2")

        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime(os.path.join(source, "file"), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()

        with open(os.path.join(destination, "file")) as f:
            assert f.read() == "2"

    def test_file_added(self, new_dir):
        source = "source"
        destination = "destination"
        os.mkdir(source)
        os.mkdir(destination)

        with open(os.path.join(source, "file1"), "w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source, "file1"), "reference")
        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime("reference", (access_time, modify_time + 1))

        local = LocalSource(source, destination, cache_dir=new_dir)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert os.path.isfile(os.path.join(destination, "file1"))

        # Now add a new file, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source, "file2"), "w") as f:
            f.write("2")

        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime(os.path.join(source, "file2"), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert os.path.isfile(os.path.join(destination, "file2"))

    def test_directory_modified(self, new_dir):
        source = "source"
        source_dir = os.path.join(source, "dir")
        destination = "destination"
        os.makedirs(source_dir)
        os.mkdir(destination)

        with open(os.path.join(source_dir, "file1"), "w") as f:
            f.write("1")

        # Now make a reference file with a timestamp later than the file was
        # created. We'll ensure this by setting it ourselves
        shutil.copy2(os.path.join(source_dir, "file1"), "reference")
        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime("reference", (access_time, modify_time + 1))

        local = LocalSource(source, destination, cache_dir=new_dir)
        local.pull()

        # Expect no updates to be available
        assert local.check_if_outdated("reference") is False

        assert os.path.isfile(os.path.join(destination, "dir", "file1"))

        # Now add a new file to the directory, and make sure it has a timestamp
        # later than our reference (this whole test happens too fast)
        with open(os.path.join(source_dir, "file2"), "w") as f:
            f.write("2")

        access_time = os.stat("reference").st_atime
        modify_time = os.stat("reference").st_mtime
        os.utime(os.path.join(source_dir, "file2"), (access_time, modify_time + 1))

        # Expect update to be available
        assert local.check_if_outdated("reference")

        local.update()
        assert os.path.isfile(os.path.join(destination, "dir", "file2"))
