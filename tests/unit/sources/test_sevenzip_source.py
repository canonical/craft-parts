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

import os
import subprocess
from pathlib import Path
from unittest.mock import call

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import sources


@pytest.mark.http_request_handler("FakeFileHTTPRequestHandler")
class TestZipSource:
    """Tests for the zip source handler."""

    def test_pull_sevenzipfile_must_download_and_extract(
        self, new_dir, http_server, mocker, partitions
    ):
        mock_prov = mocker.patch(
            "craft_parts.sources.sevenzip_source.SevenzipSource.provision"
        )

        dest_dir = Path("src")
        dest_dir.mkdir()
        sevenzip_file_name = "test.7z"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{sevenzip_file_name}"
        )
        dirs = ProjectDirs(partitions=partitions)
        sevenzip_source = sources.SevenzipSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )

        sevenzip_source.pull()

        source_file = dest_dir / sevenzip_file_name
        assert mock_prov.mock_calls == [call(dest_dir, src=source_file)]

        with (dest_dir / sevenzip_file_name).open("r") as sevenzip_file:
            assert sevenzip_file.read() == "Test fake file"

    def test_extract_and_keep_7zfile(self, new_dir, http_server, mocker, partitions):
        check_output_mock = mocker.patch("subprocess.check_output")

        sevenzip_file_name = "test.7z"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{sevenzip_file_name}"
        )
        dest_dir = Path().absolute()
        dirs = ProjectDirs(partitions=partitions)
        sevenzip_source = sources.SevenzipSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )

        sevenzip_source.download()
        sevenzip_source.provision(dst=dest_dir, keep=True)

        source_file = sevenzip_source.part_src_dir / sevenzip_file_name
        assert check_output_mock.mock_calls == [
            call(
                [
                    "7z",
                    "x",
                    f"-o{dest_dir}",
                    os.path.join(new_dir, dest_dir, source_file),
                ],
                text=True,
            ),
            call().strip(),
        ]

    def test_pull_failure(self, new_dir, http_server, mocker, partitions):
        check_output_mock = mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "error"),
        )

        sevenzip_file_name = "test.7z"
        source = (
            f"http://{http_server.server_address[0]}:"
            f"{http_server.server_address[1]}/{sevenzip_file_name}"
        )
        dest_dir = Path().absolute()
        dirs = ProjectDirs(partitions=partitions)
        sevenzip_source = sources.SevenzipSource(
            source, dest_dir, cache_dir=new_dir, project_dirs=dirs
        )
        with pytest.raises(sources.errors.PullError) as raised:
            sevenzip_source.pull()
        source_file = sevenzip_source.part_src_dir / sevenzip_file_name

        assert check_output_mock.mock_calls == [
            call(
                [
                    "7z",
                    "x",
                    f"-o{dest_dir}",
                    os.path.join(new_dir, dest_dir, source_file),
                ],
                text=True,
            )
        ]
        assert raised.value.exit_code == 1

    def test_has_source_handler_entry(self):
        assert (
            sources._get_source_handler_class("", source_type="7z")
            is sources.SevenzipSource
        )
