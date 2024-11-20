# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

"""Utilities for executing subprocesses and handling their stdout and stderr streams."""

import os
import select
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TextIO, cast

Command = str | Path | Sequence[str | Path]
Stream = TextIO | int | None

_BUF_SIZE = 4096

# Compatibility with subprocess.DEVNULL
DEVNULL = subprocess.DEVNULL


@dataclass
class ProcessResult:
    """Describes the outcome of a process."""

    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes


class _ProcessStream:
    def __init__(self, read_fd: int, write_fd: int) -> None:
        self.read_fd = read_fd
        self.write_fd = write_fd

        self._linebuf = bytearray()
        self._streambuf = b""

    @property
    def singular(self) -> bytes:
        return self._streambuf

    def process(self) -> bytes:
        """Process any data in ``self.read_fd``, then return it."""
        data = os.read(self.read_fd, _BUF_SIZE)
        i = data.rfind(b"\n")
        if i >= 0:
            self._linebuf.extend(data[: i + 1])
            self._streambuf += self._linebuf
            os.write(self.write_fd, self._linebuf)
            self._linebuf.clear()
            self._linebuf.extend(data[i + 1 :])
            return data
        self._linebuf.extend(data)
        return b""


def run(
    command: Command,
    *,
    cwd: Path | None = None,
    stdout: Stream = None,
    stderr: Stream = None,
    check: bool = True,
) -> ProcessResult:
    """Execute a subprocess and collects its stdout and stderr streams as separate 
    accounts and a singular, combined account.

    :param command: Command to execute.
    :type Command:
    :param cwd: Path to execute in.
    :type Path | None:
    :param stdout: Handle to a fd or I/O stream to treat as stdout. None defaults
        to ``sys.stdout``, and process.DEVNULL can be passed for no printing.
    :type Stream:
    :param stderr: Handle to a fd or I/O stream to treat as stderr. None defaults
        to ``sys.stderr``, and process.DEVNULL can be passed for no printing.
    :type Stream:
    :param check: If True, a ProcessError exception will be raised if ``command``
        returns a non-zero return code.
    :type bool:

    :raises ProcessError: If process exits with a non-zero return code.
    :raises OSError: If the specified executable is not found.

    :return: A description of the process' outcome.
    :rtype: ProcessResult
    """
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )

    out_fd = _select_stream(stdout, sys.stdout.fileno())
    err_fd = _select_stream(stderr, sys.stderr.fileno())

    # stdout and stderr are guaranteed not `None` because we called with `subprocess.PIPE`
    proc_stdout = cast(IO[bytes], proc.stdout).fileno()
    proc_stderr = cast(IO[bytes], proc.stderr).fileno()

    os.set_blocking(proc_stdout, False)
    os.set_blocking(proc_stderr, False)

    out_handler = _ProcessStream(proc_stdout, out_fd)
    err_handler = _ProcessStream(proc_stderr, err_fd)
    combined = b""

    while True:
        r, _, _ = select.select([proc_stdout, proc_stderr], [], [])

        try:
            if proc_stdout in r:
                combined += out_handler.process()

            if proc_stderr in r:
                combined += err_handler.process()

        except BlockingIOError:
            pass

        except Exception:
            if stdout == DEVNULL:
                os.close(out_fd)
            if stderr == DEVNULL:
                os.close(err_fd)
            raise

        if proc.poll() is not None:
            break

    if stdout == DEVNULL:
        os.close(out_fd)
    if stderr == DEVNULL:
        os.close(err_fd)

    result = ProcessResult(
        proc.returncode, out_handler.singular, err_handler.singular, combined
    )

    if check and result.returncode != 0:
        raise ProcessError(result=result, cwd=cwd, command=command)

    return result


def _select_stream(stream: Stream, default: int) -> int:
    """Translate a ``Stream`` object into a raw FD."""
    if stream == DEVNULL:
        return os.open(os.devnull, os.O_WRONLY)
    if isinstance(stream, int):
        return stream
    if stream is None:
        return default

    return stream.fileno()


@dataclass
class ProcessError(Exception):
    """Simple error for failed processes. Generally raised if the return code of 
        a process is non-zero."""

    result: ProcessResult
    cwd: Path | None
    command: Command
