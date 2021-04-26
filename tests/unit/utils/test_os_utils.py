# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from pathlib import Path

import pytest

from craft_parts.utils import os_utils


class TestTimedWriter:
    """Check if minimum interval ensured between writes."""

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_no_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # a long time has passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time + 1
        os_utils.TimedWriter.write_text(Path("foo"), "content")
        mock_sleep.assert_not_called()

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_full_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # no time passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time
        os_utils.TimedWriter.write_text(Path("bar"), "content")
        mock_sleep.assert_called_with(pytest.approx(0.02, 0.00001))

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_partial_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # some time passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time + 0.005
        os_utils.TimedWriter.write_text(Path("baz"), "content")
        mock_sleep.assert_called_with(pytest.approx(0.015, 0.00001))


class TestTerminal:
    """Tests for terminal-related utilities."""

    @pytest.mark.parametrize(
        "isatty,term,result",
        [
            (False, "xterm", True),
            (False, "dumb", True),
            (True, "xterm", False),
            (True, "dumb", True),
        ],
    )
    def test_is_dumb_terminal(self, mocker, isatty, term, result):
        mocker.patch("os.isatty", return_value=isatty)
        mocker.patch.dict(os.environ, {"TERM": term})

        assert os_utils.is_dumb_terminal() == result
