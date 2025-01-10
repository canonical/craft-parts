# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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
import selectors
import socket
import subprocess
from typing import TextIO

import pytest
from craft_parts.utils import process

_RUN_TEST_CASES = [
    ("", ""),
    ("hello", ""),
    ("", "goodbye"),
    ("hello", "goodbye"),
]


@pytest.mark.parametrize(("out", "err"), _RUN_TEST_CASES)
def test_run(out, err):
    result = process.run(["/usr/bin/sh", "-c", f"echo {out};echo {err} >&2"])
    assert result.returncode == 0
    assert result.stdout == (out + "\n").encode()
    assert result.stderr == (err + "\n").encode()
    assert result.combined == (out + "\n" + err + "\n").encode()


@pytest.mark.parametrize(("out", "err"), _RUN_TEST_CASES)
def test_run_devnull(out, err):
    result = process.run(
        ["/usr/bin/sh", "-c", f"echo {out};echo {err} >&2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert result.returncode == 0
    assert result.stdout == b""
    assert result.stderr == b""
    assert result.combined == b""


@pytest.mark.parametrize(("out", "err"), _RUN_TEST_CASES)
def test_run_selector(out, err, new_dir):
    message = []
    selector = selectors.DefaultSelector()

    # set up unix socket
    sock_path = os.path.join(new_dir, "test.socket")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(1)

    def accept(sock: TextIO, _mask: int) -> None:
        conn, addr = sock.accept()
        selector.register(conn, selectors.EVENT_READ, read)

    def read(conn: TextIO, _mask: int) -> None:
        data = conn.recv(16)
        if not data:
            selector.unregister(conn)
            conn.close()
        else:
            message.append(data.decode())

    selector.register(sock, selectors.EVENT_READ, accept)

    result = process.run(
        [
            "/usr/bin/sh",
            "-c",
            f"echo {out};echo {err} >&2; echo -n {out}|socat - UNIX-CONNECT:{new_dir}/test.socket",
        ],
        selector=selector,
    )
    assert result.returncode == 0
    assert result.stdout == (out + "\n").encode()
    assert result.stderr == (err + "\n").encode()
    assert result.combined == (out + "\n" + err + "\n").encode()
    assert message == ([out] if out else [])
