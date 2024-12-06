# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2022 Canonical Ltd.
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
from unittest.mock import call

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import sources


@pytest.mark.http_request_handler("FakeFileHTTPRequestHandler")
class TestZipSource:
    """Tests for the zip source handler."""

    def test_pull_zipfile_must_download_and_extract(
        self, new_dir, http_server, mocker, partitions
    ):
        mock_prov = mocker.patch("craft_parts.sources.zip_source.ZipSource.provision")

        dest_dir = Path("src")
        dest_dir.mkdir()
        zip_file_name = "test.zip"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{zip_file_name}"
        )
        dirs = ProjectDirs(partitions=partitions)
        zip_source = sources.ZipSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )

        zip_source.pull()

        source_file = dest_dir / zip_file_name
        assert mock_prov.mock_calls == [call(dest_dir, src=source_file)]

        with (dest_dir / zip_file_name).open("r") as zip_file:
            assert zip_file.read() == "Test fake file"

    def test_extract_and_keep_zipfile(self, new_dir, http_server, mocker, partitions):
        mock_zip = mocker.patch("zipfile.ZipFile")

        zip_file_name = "test.zip"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{zip_file_name}"
        )
        dest_dir = Path().absolute()
        dirs = ProjectDirs(partitions=partitions)
        zip_source = sources.ZipSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )

        zip_source.download()
        zip_source.provision(dst=dest_dir, keep=True)

        source_file = zip_source.part_src_dir / zip_file_name
        mock_zip.assert_called_once_with(source_file, "r")

        with source_file.open("r") as zip_file:
            assert zip_file.read() == "Test fake file"

    def test_has_source_handler_entry(self):
        assert (
            sources._get_source_handler_class("", source_type="zip")
            is sources.ZipSource
        )
