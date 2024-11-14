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
class ForkResult:
    """Describes the outcome of a forked process."""

    returncode: int
    stdout: bytes
    stderr: bytes
    combined: bytes


def run(  # noqa: PLR0915
    command: Command,
    *,
    cwd: Path | None = None,
    stdout: Stream = None,
    stderr: Stream = None,
    check: bool = False,
) -> ForkResult:
    """Execute a subprocess and collects its stdout and stderr streams as separate accounts and a singular, combined account.

    :param command: Command to execute.
    :type Command:
    :param cwd: Path to execute in.
    :type Path | None:
    :param stdout: Handle to a fd or I/O stream to treat as stdout. None defaults to ``sys.stdout``, and fork_utils.DEVNULL can be passed for no printing.
    :type Stream:
    :param stderr: Handle to a fd or I/O stream to treat as stderr. None defaults to ``sys.stderr``, and fork_utils.DEVNULL can be passed for no printing.
    :type Stream:
    :param check: If True, a ForkError exception will be raised if ``command`` returns a non-zero return code.
    :type bool:

    :raises ForkError: If forked process exits with a non-zero return code.
    :raises OSError: If the specified executable is not found.

    :return: A description of the forked process' outcome.
    :rtype: ForkResult
    """
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )

    stdout = _select_stream(stdout, sys.stdout)
    stderr = _select_stream(stderr, sys.stderr)

    # stdout and stderr are guaranteed not `None` because we called with `subprocess.PIPE`
    fdout = cast(IO[bytes], proc.stdout).fileno()
    fderr = cast(IO[bytes], proc.stderr).fileno()

    os.set_blocking(fdout, False)
    os.set_blocking(fderr, False)

    line_out = bytearray()
    line_err = bytearray()

    out = err = comb = b""

    while True:
        r, _, _ = select.select([fdout, fderr], [], [])

        try:
            if fdout in r:
                data = os.read(fdout, _BUF_SIZE)
                i = data.rfind(b"\n")
                if i >= 0:
                    line_out.extend(data[: i + 1])
                    comb += line_out
                    out += line_out
                    print(line_out.decode("utf-8"), file=stdout, end="")
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
                    err += line_err
                    print(line_err.decode("utf-8"), file=stderr, end="")
                    line_err.clear()
                    line_err.extend(data[i + 1 :])
                else:
                    line_err.extend(data)

        except BlockingIOError:
            pass

        except Exception:
            if stdout.name == os.devnull:
                stdout.close()
            if stderr.name == os.devnull:
                stderr.close()
            raise

        if proc.poll() is not None:
            break

    if stdout.name == os.devnull:
        stdout.close()
    if stderr.name == os.devnull:
        stderr.close()

    result = ForkResult(proc.returncode, out, err, comb)

    if check and result.returncode != 0:
        raise ForkError(result=result, cwd=cwd, command=command)

    return result


def _select_stream(stream: Stream, default: TextIO) -> TextIO:
    """Translate a ``Stream`` object into a usable Python stream handle."""
    if isinstance(stream, int):
        if stream != DEVNULL:
            raise ValueError(
                f'Invalid stream "{stream}": Raw file descriptors are not supported.'
            )
        return open(os.devnull, "w")
    if stream is None:
        return default
    return stream


@dataclass
class ForkError(Exception):
    """Simple error for failed forked processes. Generally raised if the return code of a forked process is non-zero."""

    result: ForkResult
    cwd: Path | None
    command: Command
