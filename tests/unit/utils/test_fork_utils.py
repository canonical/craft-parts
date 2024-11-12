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

import sys

import pytest
from craft_parts.utils import fork_utils


@pytest.mark.parametrize(("stdout", "expected"), [(None, -1), (5, 5)])
def test_stream_selection(
    stdout: fork_utils.Stream, expected: fork_utils.Stream
) -> None:
    handler = fork_utils.StreamHandler(stdout)
    assert handler._true_fd == expected


# Not one of the parametrize arguments above because pytest does not seem to allocate a sys.stdout in the decorator stage
def test_stream_fileno() -> None:
    handler = fork_utils.StreamHandler(sys.stdout)
    assert handler._true_fd == sys.stdout.fileno()


def test_pipe_write(capfd) -> None:
    handler = fork_utils.StreamHandler(sys.stdout)
    handler.start()
    handler.write(bytearray("is anybody listening?", "utf-8"))
    handler.join()

    assert capfd.readouterr().out == "is anybody listening?"
    assert handler.collected == b"is anybody listening?"


def test_file_write(tmpdir) -> None:
    with open(tmpdir / "foo", "w") as fout:
        handler = fork_utils.StreamHandler(fout)
        handler.start()
        handler.write(bytearray("is anybody listening now?", "utf-8"))
        handler.join()

    assert handler.collected == b"is anybody listening now?"
    with open(tmpdir / "foo") as fin:
        assert fin.read() == "is anybody listening now?"
