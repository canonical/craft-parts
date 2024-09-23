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

import http.server
import os
import pathlib
import tempfile
import threading
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

import pytest
import xdg  # type: ignore[import]
from craft_parts.features import Features

from . import fake_servers
from .fake_snap_command import FakeSnapCommand
from .fake_snapd import FakeSnapd


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "http_request_handler(handler): set a fake HTTP request handler"
    )


@pytest.fixture
def new_dir(monkeypatch, tmpdir):
    """Change to a new temporary directory."""
    monkeypatch.chdir(tmpdir)
    return tmpdir


@pytest.fixture
def new_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def tmp_homedir_path():
    """A non-hidden temporary directory in the user's home directory.

    This works around temporary directories being of tmpfs and is an accessible
    location for snaps with the 'home' plug like chisel.
    """
    with tempfile.TemporaryDirectory(
        prefix="craft-parts-tests", dir=pathlib.Path.home()
    ) as tmp_dir:
        yield pathlib.Path(tmp_dir)


@pytest.fixture
def new_homedir_path(monkeypatch, tmp_homedir_path):
    """Change to a new temporary directory in the user's home directory.

    This works around temporary directories sometimes being on tmpfs, which doesn't support xattrs.
    """
    monkeypatch.chdir(tmp_homedir_path)
    return tmp_homedir_path


@pytest.fixture
def mock_chdir(monkeypatch):
    mock_fn = mock.Mock(spec=os.chdir)
    monkeypatch.setattr(os, "chdir", mock_fn)
    return mock_fn


@pytest.fixture
def mock_chroot(monkeypatch):
    mock_fn = mock.Mock(spec=os.chroot)
    monkeypatch.setattr(os, "chroot", mock_fn)
    return mock_fn


@pytest.fixture
def enable_overlay_feature():
    assert Features().enable_overlay is False
    Features.reset()
    Features(enable_overlay=True)

    yield

    Features.reset()


@pytest.fixture
def enable_partitions_feature():
    assert Features().enable_partitions is False
    Features.reset()
    Features(enable_partitions=True)

    yield

    Features.reset()


@pytest.fixture
def partitions():
    if Features().enable_partitions:
        return ["default", "mypart", "yourpart"]
    return None


@pytest.fixture
def enable_all_features():
    assert Features().enable_overlay is False
    assert Features().enable_partitions is False
    Features.reset()
    Features(enable_overlay=True, enable_partitions=True)

    yield

    Features.reset()


@pytest.fixture(autouse=True)
def temp_xdg(tmpdir, mocker):
    """Use a temporary locaction for XDG directories."""

    mocker.patch(
        "xdg.BaseDirectory.xdg_config_home", new=os.path.join(tmpdir, ".config")
    )
    mocker.patch("xdg.BaseDirectory.xdg_data_home", new=os.path.join(tmpdir, ".local"))
    mocker.patch("xdg.BaseDirectory.xdg_cache_home", new=os.path.join(tmpdir, ".cache"))
    mocker.patch(
        "xdg.BaseDirectory.xdg_config_dirs",
        new=[
            xdg.BaseDirectory.xdg_config_home  # pyright: ignore[reportGeneralTypeIssues]
        ],
    )
    mocker.patch(
        "xdg.BaseDirectory.xdg_data_dirs",
        new=[
            xdg.BaseDirectory.xdg_data_home  # pyright: ignore[reportGeneralTypeIssues]
        ],
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


# XXX: check windows compatibility, explore if fixture setup can skip itself


@pytest.fixture(scope="class")
def fake_snapd():
    """Provide a fake snapd server."""

    server = FakeSnapd()

    snapd_fake_socket_path = str(tempfile.mkstemp()[1])
    os.unlink(snapd_fake_socket_path)

    socket_path_patcher = mock.patch(
        "craft_parts.packages.snaps.get_snapd_socket_path_template"
    )
    escaped_path = snapd_fake_socket_path.replace("/", "%2F")
    mock_socket_path = socket_path_patcher.start()
    mock_socket_path.return_value = f"http+unix://{escaped_path}/v2/{{}}"

    thread = server.start_fake_server(snapd_fake_socket_path)

    yield server

    server.stop_fake_server(thread)
    socket_path_patcher.stop()


@pytest.fixture
def fake_snap_command(mocker):
    """Mock the snap command."""
    return FakeSnapCommand(mocker)


@pytest.fixture
def dependency_fixture(new_dir):
    """Fixture factory for dependencies."""

    def create_dependency_fixture(
        name: str,
        broken: bool = False,  # noqa: FBT001, FBT002
        invalid: bool = False,  # noqa: FBT001, FBT002
        output: str | None = None,
    ) -> Path:
        """Creates a mock executable dependency.

        :param name: name of the dependency
        :param broken: if true, the dependency will return error code 33
        :param invalid: if true, the dependency will return an empty string
        :param output: text for dependency to return, default is `1.0.0`

        :return: path to dependency
        """
        dependency_bin = Path(new_dir, "mock_bin", name)
        dependency_bin.parent.mkdir(exist_ok=True)
        if broken:
            dependency_bin.write_text("#!/bin/sh\nexit 33")
        elif invalid:
            dependency_bin.touch()
        elif output:
            dependency_bin.write_text(f'#!/bin/sh\necho "{output}"')
        else:
            dependency_bin.write_text('#!/bin/sh\necho "1.0.0"')
        dependency_bin.chmod(0o755)
        return dependency_bin

    return create_dependency_fixture


class ChmodCall(NamedTuple):
    """Record of a call to os.chmod()."""

    owner: int
    group: int
    kwargs: dict[str, Any]


@pytest.fixture
def mock_chown(mocker) -> dict[str, ChmodCall]:
    """Mock os.chown() and keep a record of calls to it.

    The returned object is a dict where the keys match the ``path`` parameter of the
    os.chown() call and the values are ``ChmodCall`` tuples containing the other parameters.
    """
    calls = {}

    def fake_chown(path, uid, gid, **kwargs):
        calls[path] = ChmodCall(owner=uid, group=gid, kwargs=kwargs)

    mocker.patch.object(os, "chown", side_effect=fake_chown)

    return calls
