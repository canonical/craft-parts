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
from typing import Union, Sequence, TextIO

Command = Union[str, Path, Sequence[Union[str, Path]]]
Stream = int | TextIO | None

_BUF_SIZE = 4096

@dataclass
class ForkResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes

class StreamHandler(threading.Thread):
    def __init__(self, true_fd: Stream) -> None:
        super().__init__()
        if isinstance(true_fd, int):
            self._true_fd = true_fd
        elif isinstance(true_fd, TextIO):
            self._true_fd = true_fd.fileno()
        else:
            self._true_fd = -1

        self.collected = b""
        self._read_pipe, self._write_pipe = os.pipe()
        self._stop_flag = False

    def run(self) -> None:
        while True:
            r, _, _ = select.select([self._read_pipe], [], [])

            try:
                if self._read_pipe in r:
                    data = os.read(self._read_pipe, _BUF_SIZE)
                    self.collected += data
                    if self._true_fd != -1:
                        os.write(self._true_fd, data)
            
            except BlockingIOError:
                pass

            if self._stop_flag:
                break

    def join(self, timeout: float | None = None) -> None:
        if self._stop_flag:
            return
        self._stop_flag = True
        super().join(timeout)
        os.close(self._read_pipe)
        os.close(self._write_pipe)

    def write(self, data: bytearray) -> None:
        os.write(self._write_pipe, data)


def run(command: Command, cwd: Path, stdout: Stream, stderr: Stream) -> ForkResult:
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
            out.join()
            err.join()
            break

    return ForkResult(proc.returncode, out.collected, err.collected, comb)
