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

from craft_parts import ctl


class TestClient:
    """Verify the ctl client."""

    def test_call_function(self, new_dir, mocker):
        call_fifo = Path("call_fifo")
        feedback_fifo = Path("feedback_fifo")

        call_fifo.touch()
        feedback_fifo.touch()

        mocker.patch.dict(
            os.environ,
            {"PARTS_CALL_FIFO": "call_fifo", "PARTS_FEEDBACK_FIFO": "feedback_fifo"},
        )
        ctl.client("pull", ["whatever"])

        msg = call_fifo.read_text()
        assert msg == '{"function": "pull", "args": ["whatever"]}'

    def test_call_function_with_feedback(self, new_dir, mocker):
        call_fifo = Path("call_fifo")
        feedback_fifo = Path("feedback_fifo")

        call_fifo.touch()
        feedback_fifo.write_text("hello there!")

        mocker.patch.dict(
            os.environ,
            {"PARTS_CALL_FIFO": "call_fifo", "PARTS_FEEDBACK_FIFO": "feedback_fifo"},
        )
        with pytest.raises(RuntimeError) as raised:
            ctl.client("pull", ["whatever"])

        assert str(raised.value) == "hello there!"

    def test_call_function_without_call_fifo(self, new_dir, mocker):
        call_fifo = Path("call_fifo")
        feedback_fifo = Path("feedback_fifo")

        call_fifo.touch()
        feedback_fifo.touch()

        mocker.patch.dict(os.environ, {"PARTS_FEEDBACK_FIFO": "feedback_fifo"})
        with pytest.raises(RuntimeError) as raised:
            ctl.client("pull", ["whatever"])

        assert str(raised.value) == (
            "'PARTS_CALL_FIFO' environment variable must be defined.\n"
            "Note that this utility is designed for use only in part scriptlets."
        )

    def test_call_function_without_feedback_fifo(self, new_dir, mocker):
        call_fifo = Path("call_fifo")
        feedback_fifo = Path("feedback_fifo")

        call_fifo.touch()
        feedback_fifo.touch()

        mocker.patch.dict(os.environ, {"PARTS_CALL_FIFO": "call_fifo"})
        with pytest.raises(RuntimeError) as raised:
            ctl.client("pull", ["whatever"])

        assert str(raised.value) == (
            "'PARTS_FEEDBACK_FIFO' environment variable must be defined.\n"
            "Note that this utility is designed for use only in part scriptlets."
        )

    def test_call_invalid_function(self, new_dir):
        with pytest.raises(RuntimeError) as raised:
            ctl.client("grok", ["whatever"])

        assert str(raised.value) == "invalid command 'grok'"
