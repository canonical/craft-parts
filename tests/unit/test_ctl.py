# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

import pytest
from craft_parts.ctl import CraftCtl


class _FakeSocket:
    def __init__(self, recv: bytes):
        self._buffer = recv
        self.data: bytes = b""

    def listen(self, n: int):
        pass

    def send(self, data: bytes) -> None:
        self.data = data

    def recv(self, n: int) -> bytes:
        return self._buffer

    def connect(self, path: str):
        pass


class TestClient:
    """Verify the ctl client."""

    def test_call_command(self, new_dir, mocker):
        fake_socket = _FakeSocket(b"")
        mocker.patch("socket.socket", return_value=fake_socket)
        mocker.patch.dict(os.environ, {"PARTS_CTL_SOCKET": "fake"})

        CraftCtl.run("default", ["whatever"])

        assert fake_socket.data == b'{"function": "default", "args": ["whatever"]}'

    def test_call_command_with_ok_feedback(self, new_dir, mocker):
        fake_socket = _FakeSocket(b"OK hello there!")
        mocker.patch("socket.socket", return_value=fake_socket)
        mocker.patch.dict(os.environ, {"PARTS_CTL_SOCKET": "fake"})

        retval = CraftCtl.run("get", ["whatever"])

        assert retval == "hello there!"

    def test_call_command_with_error_feedback(self, new_dir, mocker):
        fake_socket = _FakeSocket(b"ERR hello there!")
        mocker.patch("socket.socket", return_value=fake_socket)
        mocker.patch.dict(os.environ, {"PARTS_CTL_SOCKET": "fake"})

        with pytest.raises(RuntimeError) as raised:
            CraftCtl.run("default", ["whatever"])

        assert str(raised.value) == "hello there!"

    def test_call_command_without_ctl_socket(self, new_dir, mocker):
        fake_socket = _FakeSocket(b"OK hello there!")
        mocker.patch("socket.socket", return_value=fake_socket)

        with pytest.raises(RuntimeError) as raised:
            CraftCtl.run("default", ["whatever"])

        assert str(raised.value) == (
            "'PARTS_CTL_SOCKET' environment variable must be defined.\n"
            "Note that this utility is designed for use only in part scriptlets."
        )

    def test_call_invalid_command(self, new_dir):
        with pytest.raises(RuntimeError) as raised:
            CraftCtl.run("grok", ["whatever"])

        assert str(raised.value) == "invalid command 'grok'"
