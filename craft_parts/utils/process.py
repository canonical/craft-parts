# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024-2025 Canonical Ltd.
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
import selectors
import subprocess
import sys
from collections.abc import Generator, Sequence
from contextlib import closing, contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import IO, TextIO

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

        # (Mostly) optimize away the process function if the read handle is empty
        if self.read_fd == DEVNULL:
            self.process = self._process_nothing  # type: ignore[method-assign]

    @property
    def singular(self) -> bytes:
        return self._streambuf

    def process(self) -> bytes:
        """Forward any data from ``self.read_fd`` to ``self.write_fd`` and return a copy of it.

        Does nothing if ``read_fd`` is DEVNULL.
        """
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

    def _process_nothing(self) -> bytes:
        """Do nothing."""
        return b""


def run(
    command: Command,
    *,
    cwd: Path | None = None,
    stdout: Stream = None,
    stderr: Stream = None,
    check: bool = True,
    selector: selectors.BaseSelector | None = None,
) -> ProcessResult:
    """Execute a subprocess and collect its output.

    This function collects the stdout and stderr streams as separate
    accounts and a singular, combined account.

    :param command: Command to execute.
    :param cwd: Path to execute in.
    :param stdout: Handle to a fd or I/O stream to treat as stdout. None defaults
        to ``sys.stdout``, and process.DEVNULL can be passed for no printing or
        stream capturing.
    :param stderr: Handle to a fd or I/O stream to treat as stderr. None defaults
        to ``sys.stderr``, and process.DEVNULL can be passed for no printing or
        stream capturing.
    :param check: If True, a ProcessError exception will be raised if ``command``
        returns a non-zero return code.
    :param selector: If defined, use the caller-supplied selector instead of
        creating a new one.

    :raises ProcessError: If process exits with a non-zero return code.
    :raises OSError: If the specified executable is not found.

    :return: A description of the process' outcome.
    :rtype: ProcessResult
    """
    # Optimized base case - no custom handlers or redirections at all
    if not selector and stdout == DEVNULL and stderr == DEVNULL:
        result_sp = subprocess.run(
            command, stdout=DEVNULL, stderr=DEVNULL, cwd=cwd, check=False
        )
        result = ProcessResult(result_sp.returncode, b"", b"", b"", command)
        if check:
            result.check_returncode()
        return result

    proc = subprocess.Popen(
        command,
        stdout=DEVNULL if stdout == DEVNULL else subprocess.PIPE,
        stderr=DEVNULL if stderr == DEVNULL else subprocess.PIPE,
        cwd=cwd,
    )

    with (
        _select_stream(stdout, sys.stdout) as out_fd,
        _select_stream(stderr, sys.stderr) as err_fd,
    ):
        # Set up select library with any streams that need monitoring
        selector = selector or selectors.DefaultSelector()
        out_handler = _get_stream_handler(proc.stdout, out_fd, selector)
        err_handler = _get_stream_handler(proc.stderr, err_fd, selector)

        with closing(BytesIO()) as combined_io:
            while True:
                try:
                    # Time out if we don't have any event to handle
                    for key, mask in selector.select(0.1):
                        if isinstance(key.data, _ProcessStream):
                            # Handle i/o stream processing.
                            combined_io.write(key.data.process())
                        else:
                            # Generic handlers from caller selector.
                            callback = key.data
                            callback(key.fileobj, mask)
                except BlockingIOError:
                    pass

                if proc.poll() is not None:
                    combined = combined_io.getvalue()
                    break

    stdout_res = out_handler.singular if out_handler else b""
    stderr_res = err_handler.singular if err_handler else b""

    result = ProcessResult(
        proc.returncode,
        stdout_res,
        stderr_res,
        combined,
        command,
    )

    if check:
        result.check_returncode()

    return result


@contextmanager
def _select_stream(stream: Stream, default_stream: TextIO) -> Generator[int]:
    """Select and return an appropriate raw file descriptor.

    Based on the input, this function returns a raw integer file descriptor according
    to what is expected from the ``run()`` function in this same module.

    If determining the file handle involves opening our own, this generator handles
    closing it afterwards.
    """
    if stream == DEVNULL:
        with open(os.devnull, "wb") as s:
            yield s.fileno()
    elif isinstance(stream, int):
        yield stream
    elif stream is None:
        yield default_stream.fileno()
    else:
        yield stream.fileno()


def _get_stream_handler(
    proc_std: IO[bytes] | None, write_fd: int, selector: selectors.BaseSelector
) -> _ProcessStream | None:
    """Create a stream handle if necessary and register it."""
    if not proc_std:
        return None

    proc_fd = proc_std.fileno()
    os.set_blocking(proc_fd, False)
    handler = _ProcessStream(proc_fd, write_fd)
    selector.register(proc_std, selectors.EVENT_READ, handler)
    return handler


@dataclass
class ProcessError(Exception):
    """Simple error for failed processes.

    Generally raised if the return code of a process is non-zero.
    """

    result: ProcessResult
