# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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
import requests
from craft_parts import ProjectDirs, sources


@pytest.mark.http_request_handler("FakeFileHTTPRequestHandler")
class TestFileSource:
    """Tests for the plain file source handler."""

    def test_pull_file_must_download_to_sourcedir(
        self, new_dir, mocker, http_server, partitions
    ):
        dest_dir = Path("parts/foo/src")
        dest_dir.mkdir(parents=True)
        file_name = "test.tar"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{file_name}"
        )

        dirs = ProjectDirs(partitions=partitions)
        file_source = sources.FileSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )
        file_source.pull()

        source_file = dest_dir / file_name
        assert source_file.read_text() == "Test fake file"

    def test_pull_twice_downloads_once(self, new_dir, mocker, http_server, partitions):
        """If a source checksum is defined, the cache should be tried first."""

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
        file_source = sources.FileSource(
            source,
            Path(),
            cache_dir=new_dir,
            source_checksum=expected_checksum,
            project_dirs=dirs,
        )

        download_spy = mocker.spy(requests, "get")
        file_source.pull()
        file_source.pull()
        assert download_spy.call_count == 1
