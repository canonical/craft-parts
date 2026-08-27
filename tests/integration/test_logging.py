# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
import logging
import sys
import textwrap
from pathlib import Path

import craft_parts
from craft_parts import main


def setup_function():
    craft_parts.Features.reset()


def teardown_function():
    craft_parts.Features.reset()


parts_yaml = textwrap.dedent(
    """
    parts:
      foo:
        plugin: nil
        build-packages: [libc6]
        # Note that this will fail if core20 is not already installed and the
        # test is executed as a regular user
        build-snaps: [core20]
        stage-packages: [hello]
    """
)


def test_logging_info(new_dir, caplog, monkeypatch):
    """Test some expected INFO-level log messages from whole-program execution."""
    caplog.set_level(logging.INFO, logger="craft_parts")
    Path("parts.yaml").write_text(parts_yaml)

    monkeypatch.setattr(sys, "argv", ["build"])

    main.main()

    assert "Installing build-packages" in caplog.text
    assert "Installing build-snaps" in caplog.text
    assert "Fetching stage-packages" in caplog.text
