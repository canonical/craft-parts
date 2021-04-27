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

import http.server
import os
import threading

import pytest
import xdg  # type: ignore

from . import fake_servers


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "http_request_handler(handler): set a fake HTTP request handler"
    )


@pytest.fixture
def new_dir(tmpdir):
    """Change to a new temporary directory."""

    cwd = os.getcwd()
    os.chdir(tmpdir)

    yield tmpdir

    os.chdir(cwd)


@pytest.fixture(autouse=True)
def temp_xdg(tmpdir, mocker):
    """Use a temporary locaction for XDG directories."""

    mocker.patch(
        "xdg.BaseDirectory.xdg_config_home", new=os.path.join(tmpdir, ".config")
    )
    mocker.patch("xdg.BaseDirectory.xdg_data_home", new=os.path.join(tmpdir, ".local"))
    mocker.patch("xdg.BaseDirectory.xdg_cache_home", new=os.path.join(tmpdir, ".cache"))
    mocker.patch(
        "xdg.BaseDirectory.xdg_config_dirs", new=[xdg.BaseDirectory.xdg_config_home]
    )
    mocker.patch(
        "xdg.BaseDirectory.xdg_data_dirs", new=[xdg.BaseDirectory.xdg_data_home]
    )
    mocker.patch.dict(os.environ, {"XDG_CONFIG_HOME": os.path.join(tmpdir, ".config")})


@pytest.fixture(scope="class")
def http_server(request):
    """Provide an http server with configurable request handlers."""

    marker = request.node.get_closest_marker("http_request_handler")
    if marker:
        handler = getattr(fake_servers, marker.args[0])
    else:
        handler = fake_servers.DummyHTTPRequestHandler

    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    yield server

    server.shutdown()
    server.server_close()
    server_thread.join()
