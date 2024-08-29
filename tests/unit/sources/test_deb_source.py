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


import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import sources
from craft_parts.utils import os_utils


@pytest.fixture
def mock_process_run(mocker):
    return mocker.patch.object(os_utils, "process_run", autospec=True)


@pytest.mark.http_request_handler("FakeFileHTTPRequestHandler")
def test_pull_debfile_must_download_and_extract(
    tmp_path, http_server, mocker, mock_process_run, partitions
):
    dest_dir = tmp_path / "src"
    dest_dir.mkdir()
    deb_file_name = "test.deb"
    source = (
        f"http://{http_server.server_address[0]}:"
        f"{http_server.server_address[1]}/{deb_file_name}"
    )
    dirs = ProjectDirs(partitions=partitions)
    deb_source = sources.DebSource(
        source, dest_dir, cache_dir=tmp_path, project_dirs=dirs
    )
    deb_source.pull()

    mock_process_run.assert_called_once_with(
        command=["dpkg-deb", "--extract", str(dest_dir / deb_file_name), str(dest_dir)],
        log_func=mocker.ANY,
    )
