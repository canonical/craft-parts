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

import errno
import os
import select
import subprocess
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TextIO, cast

Command = str | Path | Sequence[str | Path]
Stream = int | TextIO | None

_BUF_SIZE = 4096


@dataclass
class ForkResult:
    """Describes the outcome of a forked process."""

    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes


class StreamHandler(threading.Thread):
    """Helper class for splitting a stream into two destinations: the stream handed to it via ``fd`` and the ``self.collected`` field."""

    def __init__(self, fd: Stream) -> None:
        """Initialize a StreamHandler.

        :param fd: The "real" file descriptor to print to.
        """
        super().__init__()
        if isinstance(fd, int):
            self._true_fd = fd
        elif isinstance(fd, TextIO):
            self._true_fd = fd.fileno()
        else:
            self._true_fd = -1

        self._collected = b""
        self._read_pipe, self._write_pipe = os.pipe()
        os.set_blocking(self._read_pipe, False)
        os.set_blocking(self._write_pipe, False)
        self._stop_flag = False

    @property
    def collected(self) -> bytes:
        """Data collected from stream over the lifetime of this handler."""
        return self._collected

    def run(self) -> None:
        """Constantly check if any data has been sent, then duplicate it if so.

        :raises RuntimeError: If the file descriptor passed at initialization is closed before `.stop()` is called.
        :raises OSError: If an internal error occurs preventing this function from reading or writing from pipes.
        """
        while not self._stop_flag:
            r, _, _ = select.select([self._read_pipe], [], [])

            try:
                if self._read_pipe in r:
                    data = os.read(self._read_pipe, _BUF_SIZE)
                    self._collected += data
                    if self._true_fd != -1:
                        try:
                            os.write(self._true_fd, data)
                        except OSError:
                            raise RuntimeError(
                                "Stream handle given to StreamHandler object was unreachable. Was it closed early?"
                            )

            except BlockingIOError:
                pass

            except OSError as e:
                # Occurs when the pipe closes while trying to read from it. This generally happens if the program
                # responsible for the pipe is stopped. Since that makes it expected behavior for the pipe to be
                # closed, we can discard this specific error
                if e.errno == errno.EBADF:
                    return
                raise

    def stop(self) -> None:
        """Stop monitoring the stream and close all associated pipes."""
        if self._stop_flag:
            return
        self._stop_flag = True
        os.close(self._read_pipe)
        os.close(self._write_pipe)

    def write(self, data: bytearray) -> None:
        """Send a message to write to the channels managed by this instance.

        :param data: Byte data to write
        """
        os.write(self._write_pipe, data)


def run(
    command: Command, cwd: Path, stdout: Stream, stderr: Stream, *, check: bool = False
) -> ForkResult:
    """Execute a subprocess and collects its stdout and stderr streams as separate accounts and a singular, combined account.

    :param command: Command to execute.
    :type Command:
    :param cwd: Path to execute in.
    :type Path:
    :param stdout: Handle to a fd or I/O stream to treat as stdout
    :type Stream:
    :param stderr: Handle to a fd or I/O stream to treat as stderr
    :type Stream:
    :param check: If True, a ForkError exception will be raised if ``command`` returns a non-zero return code.
    :type bool:

    :raises ForkError: If forked process exits with a non-zero return code

    :return: A description of the forked process' outcome
    :rtype: ForkResult
    """
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )

    comb = b""

    # stdout and stderr are guaranteed not `None` because we called with `subprocess.PIPE`
    fdout = cast(IO[bytes], proc.stdout).fileno()
    fderr = cast(IO[bytes], proc.stderr).fileno()

    os.set_blocking(fdout, False)
    os.set_blocking(fderr, False)

    line_out = bytearray()
    line_err = bytearray()

    out = StreamHandler(stdout)
    err = StreamHandler(stderr)
    out.start()
    err.start()
    while True:
        r, _, _ = select.select([fdout, fderr], [], [])

        try:
            if fdout in r:
                data = os.read(fdout, _BUF_SIZE)
                i = data.rfind(b"\n")
                if i >= 0:
                    line_out.extend(data[: i + 1])
                    comb += line_out
                    out.write(line_out)
                    line_out.clear()
                    line_out.extend(data[i + 1 :])
                else:
                    line_out.extend(data)

            if fderr in r:
                data = os.read(fderr, _BUF_SIZE)
                i = data.rfind(b"\n")
                if i >= 0:
                    line_err.extend(data[: i + 1])
                    comb += line_err
                    err.write(line_err)
                    line_err.clear()
                    line_err.extend(data[i + 1 :])
                else:
                    line_err.extend(data)

        except BlockingIOError:
            pass

        if proc.poll() is not None:
            out.stop()
            err.stop()
            break

    result = ForkResult(proc.returncode, out.collected, err.collected, comb)

    if check and result.returncode != 0:
        raise ForkError(result=result, cwd=cwd, command=command)

    return result


@dataclass
class ForkError(Exception):
    """Simple error for failed forked processes. Generally raised if the return code of a forked process is non-zero."""

    result: ForkResult
    cwd: Path
    command: Command
