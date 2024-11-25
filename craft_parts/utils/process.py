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
from collections.abc import Generator, Sequence
from contextlib import closing, contextmanager
from dataclasses import dataclass
from io import BytesIO
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
    command: Command

    def check_returncode(self) -> None:
        """Raise an exception if the process returned non-zero."""
        if self.returncode != 0:
            raise ProcessError(self)


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
        """Forward any data from ``self.read_fd`` to ``self.write_fd`` and return a copy of it."""
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
    """Execute a subprocess and collect its output.

    This function collects the stdout and stderr streams as separate
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

    with (
        _select_stream(stdout, sys.stdout.fileno()) as out_fd,
        _select_stream(stderr, sys.stderr.fileno()) as err_fd,
    ):
        # stdout and stderr are guaranteed not `None` because we called with `subprocess.PIPE`
        proc_stdout = cast(IO[bytes], proc.stdout).fileno()
        proc_stderr = cast(IO[bytes], proc.stderr).fileno()

        os.set_blocking(proc_stdout, False)
        os.set_blocking(proc_stderr, False)

        out_handler = _ProcessStream(proc_stdout, out_fd)
        err_handler = _ProcessStream(proc_stderr, err_fd)

        with closing(BytesIO()) as combined_io:
            while True:
                r, _, _ = select.select([proc_stdout, proc_stderr], [], [])

                try:
                    if proc_stdout in r:
                        combined_io.write(out_handler.process())

                    if proc_stderr in r:
                        combined_io.write(err_handler.process())

                except BlockingIOError:
                    pass

                if proc.poll() is not None:
                    combined = combined_io.getvalue()
                    break

    result = ProcessResult(
        proc.returncode,
        out_handler.singular,
        err_handler.singular,
        combined,
        command,
    )

    if check and result.returncode != 0:
        raise ProcessError(result)

    return result


@contextmanager
def _select_stream(stream: Stream, default: int) -> Generator[int]:
    """Select and return an appropriate raw file descriptor.

    Based on the input, this function returns a raw integer file descriptor according
    to what is expected from the ``run()`` function in this same module.

    If determining the file handle involves opening our own, this generator handles
    closing it afterwards.
    """
    s: int
    close = False
    if stream == DEVNULL:
        s = os.open(os.devnull, os.O_WRONLY)
        close = True
    elif isinstance(stream, int):
        s = stream
    elif stream is None:
        s = default
    else:
        s = stream.fileno()

    try:
        yield s
    finally:
        if close:
            os.close(s)


@dataclass
class ProcessError(Exception):
    """Simple error for failed processes.

    Generally raised if the return code of a process is non-zero.
    """

    result: ProcessResult
