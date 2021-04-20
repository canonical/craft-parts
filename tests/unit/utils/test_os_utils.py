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

import pytest

from craft_parts.utils import os_utils


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
