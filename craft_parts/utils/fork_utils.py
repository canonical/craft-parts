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

from dataclasses import dataclass
import os
from pathlib import Path
import select
import subprocess
import threading
from typing import Sequence, TextIO

Command = str | Path | Sequence[str | Path]
Stream = int | TextIO | None

_BUF_SIZE = 4096

@dataclass
class ForkResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes

class StreamHandler(threading.Thread):
    """Helper class for splitting a stream into two destinations: the stream handed to it via `fd` and the `self.collected` field."""
    def __init__(self, fd: Stream) -> None:
        """`true_fd` should be the file descriptor that this instance writes to"""
        super().__init__()
        if isinstance(fd, int):
            self._true_fd = fd
        elif isinstance(fd, TextIO):
            self._true_fd = fd.fileno()
        else:
            self._true_fd = -1

        self.collected = b""
        self._read_pipe, self._write_pipe = os.pipe()
        os.set_blocking(self._read_pipe, False)
        os.set_blocking(self._write_pipe, False)
        self._stop_flag = False

    def run(self) -> None:
        """Constantly check if `self._read_pipe` has any data ready to be read, then duplicate it if so"""
        while not self._stop_flag:
            r, _, _ = select.select([self._read_pipe], [], [])

            try:
                if self._read_pipe in r:
                    data = os.read(self._read_pipe, _BUF_SIZE)
                    self.collected += data
                    if self._true_fd != -1:
                        try:
                            os.write(self._true_fd, data)
                        except OSError:
                            raise RuntimeError("Stream handle given to StreamHandler object was unreachable. Was it closed early?")
            
            except BlockingIOError:
                pass

            except OSError as e:
                # Occurs when the pipe closes while trying to read from it. This generally happens if the program
                # responsible for the pipe is stopped. Since that makes it expected behavior for the pipe to be 
                # closed, we can discard this specific error
                if e.errno == 9:
                    return
                else:
                    raise e

    def stop(self) -> None:
        """Stops monitoring the stream and closes all associated pipes"""
        if self._stop_flag:
            return
        self._stop_flag = True
        os.close(self._read_pipe)
        os.close(self._write_pipe)

    def write(self, data: bytearray) -> None:
        """Sends a message to write to the channels managed by this instance"""
        os.write(self._write_pipe, data)


def run(command: Command, cwd: Path, stdout: Stream, stderr: Stream, check: bool = False) -> ForkResult:
    """Executes a subprocess and collects its stdout and stderr streams as separate accounts and a singular, combined account.
        Args:
            command: Command to execute.
            cwd: Path to execute in.
            stdout: Handle to a fd or I/O stream to treat as stdout
            stderr: Handle to a fd or I/O stream to treat as stderr

        Raises:
            ForkError when forked process exits with a non-zero return code
    """
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)

    comb = b""
    
    fdout = proc.stdout.fileno() # type: ignore # stdout (and stderr below) are guaranteed not `None` because we called with `subprocess.PIPE`
    fderr = proc.stderr.fileno() # type: ignore

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
                i = data.rfind(b'\n')
                if i >= 0:
                    line_out.extend(data[:i+1])
                    comb += line_out
                    out.write(line_out)
                    line_out.clear()
                    line_out.extend(data[i+1:])
                else:
                    line_out.extend(data)

            if fderr in r:
                data = os.read(fderr, _BUF_SIZE)
                i = data.rfind(b'\n')
                if i >= 0:
                    line_err.extend(data[:i+1])
                    comb += line_err
                    err.write(line_err)
                    line_err.clear()
                    line_err.extend(data[i+1:])
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
