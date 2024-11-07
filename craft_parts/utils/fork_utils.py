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
from typing import cast, Union, Sequence

Command = Union[str, Path, Sequence[Union[str, Path]]]

BUF_SIZE = 4096

@dataclass
class ForkResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes

def run(command: Command, cwd: Path) -> ForkResult:
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)

    stdout = stderr = comb = b""
    
    fdout = proc.stdout.fileno() # type: ignore # stdout (and stderr below) are guaranteed not `None` because we called with `subprocess.PIPE`
    fderr = proc.stderr.fileno() # type: ignore

    os.set_blocking(fdout, False)
    os.set_blocking(fderr, False)

    line_out = bytearray()
    line_err = bytearray()

    while True:
        r, _, _ = select.select([fdout, fderr], [], [])

        try:
            if fdout in r:
                data = os.read(fdout, BUF_SIZE)
                i = data.rfind(b'\n')
                if i >= 0:
                    line_out.extend(data[:i+1])
                    comb += line_out
                    stdout += line_out
                    line_out.clear()
                    line_out.extend(data[i+1:])
                else:
                    line_out.extend(data)

            if fderr in r:
                data = os.read(fderr, BUF_SIZE)
                i = data.rfind(b'\n')
                if i >= 0:
                    line_err.extend(data[:i+1])
                    comb += line_err
                    stderr += line_err
                    line_err.clear()
                    line_err.extend(data[i+1:])
                else:
                    line_err.extend(data)

        except BlockingIOError:
            pass

        if proc.poll() is not None:
            break

    return ForkResult(proc.returncode, stdout, stderr, comb)
