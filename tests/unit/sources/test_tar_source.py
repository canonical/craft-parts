# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
import tarfile
from pathlib import Path
from unittest.mock import call

import pytest
import requests
from craft_parts import ProjectDirs
from craft_parts.sources import sources


@pytest.mark.http_request_handler("FakeFileHTTPRequestHandler")
class TestTarSource:
    """Tests for the tar source handler."""

    def test_pull_tarball_must_download_to_sourcedir(
        self, new_dir, mocker, http_server, partitions
    ):
        mock_prov = mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

        dest_dir = Path("parts/foo/src")
        dest_dir.mkdir(parents=True)
        tar_file_name = "test.tar"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{tar_file_name}"
        )

        dirs = ProjectDirs(partitions=partitions)
        tar_source = sources.TarSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )
        tar_source.pull()

        source_file = dest_dir / tar_file_name
        assert mock_prov.mock_calls == [call(dest_dir, src=source_file)]

        with (dest_dir / tar_file_name).open("r") as tar_file:
            assert tar_file.read() == "Test fake file"

    def test_pull_twice_downloads_once(self, new_dir, mocker, http_server, partitions):
        """If a source checksum is defined, the cache should be tried first."""

        mocker.patch("craft_parts.sources.tar_source.TarSource.provision")

        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/test.tar"
        )

        expected_checksum = (
            "sha384/d9da1f5d54432edc8963cd817ceced83f7c6d61d3"
            "50ad76d1c2f50c4935d11d50211945ca0ecb980c04c98099"
            "085b0c3"
        )
        dirs = ProjectDirs(partitions=partitions)
        tar_source = sources.TarSource(
            source,
            Path(),
            cache_dir=new_dir,
            source_checksum=expected_checksum,
            project_dirs=dirs,
        )

        tar_source.pull()

        download_spy = mocker.spy(requests, "get")
        tar_source.pull()
        assert download_spy.call_count == 0

    def test_strip_common_prefix(self, new_dir, partitions):
        # Create tar file for testing
        os.makedirs(os.path.join("src", "test_prefix"))
        file_to_tar = os.path.join("src", "test_prefix", "test.txt")
        open(file_to_tar, "w").close()
        with tarfile.open(os.path.join("src", "test.tar"), "w") as tar:
            tar.add(file_to_tar)

        dirs = ProjectDirs(partitions=partitions)
        tar_source = sources.TarSource(
            os.path.join("src", "test.tar"),
            Path("dst"),
            cache_dir=new_dir,
            project_dirs=dirs,
        )
        os.mkdir("dst")
        tar_source.pull()

        # The 'test_prefix' part of the path should have been removed
        assert os.path.exists(os.path.join("dst", "test.txt"))

    def test_strip_common_prefix_symlink(self, new_dir, partitions):
        # Create tar file for testing
        os.makedirs(os.path.join("src", "test_prefix"))
        file_to_tar = os.path.join("src", "test_prefix", "test.txt")
        open(file_to_tar, "w").close()

        file_to_link = os.path.join("src", "test_prefix", "link.txt")
        os.symlink("./test.txt", file_to_link)
        assert os.path.islink(file_to_link)

        def check_for_symlink(tarinfo):
            assert tarinfo.issym()
            assert file_to_link == tarinfo.name
            assert file_to_tar == os.path.normpath(
                os.path.join(os.path.dirname(file_to_tar), tarinfo.linkname)
            )
            return tarinfo

        with tarfile.open(os.path.join("src", "test.tar"), "w") as tar:
            tar.add(file_to_tar)
            tar.add(file_to_link, filter=check_for_symlink)

        dirs = ProjectDirs(partitions=partitions)
        tar_source = sources.TarSource(
            os.path.join("src", "test.tar"),
            Path("dst"),
            cache_dir=new_dir,
            project_dirs=dirs,
        )
        os.mkdir("dst")
        tar_source.pull()

        # The 'test_prefix' part of the path should have been removed
        assert os.path.exists(os.path.join("dst", "test.txt"))
        assert os.path.exists(os.path.join("dst", "link.txt"))

    def test_strip_common_prefix_hardlink(self, new_dir, partitions):
        # Create tar file for testing
        os.makedirs(os.path.join("src", "test_prefix"))
        file_to_tar = os.path.join("src", "test_prefix", "test.txt")
        open(file_to_tar, "w").close()

        file_to_link = os.path.join("src", "test_prefix", "link.txt")
        os.link(file_to_tar, file_to_link)
        assert os.path.exists(file_to_link)

        def check_for_hardlink(tarinfo):
            assert tarinfo.islnk()
            assert tarinfo.issym() is False
            assert file_to_link == tarinfo.name
            assert file_to_tar == tarinfo.linkname
            return tarinfo

        with tarfile.open(os.path.join("src", "test.tar"), "w") as tar:
            tar.add(file_to_tar)
            tar.add(file_to_link, filter=check_for_hardlink)

        dirs = ProjectDirs(partitions=partitions)
        tar_source = sources.TarSource(
            os.path.join("src", "test.tar"),
            Path("dst"),
            cache_dir=new_dir,
            project_dirs=dirs,
        )
        os.mkdir("dst")
        tar_source.pull()

        # The 'test_prefix' part of the path should have been removed
        assert os.path.exists(os.path.join("dst", "test.txt"))
        assert os.path.exists(os.path.join("dst", "link.txt"))
