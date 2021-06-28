# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Helpers to invoke step execution handlers from the command line."""

import json
import logging
import os
import sys
from typing import List

logger = logging.getLogger(__name__)


def main():
    """Run the ctl client cli."""
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <command> [arguments]")
        sys.exit(1)

    cmd, param = sys.argv[1], sys.argv[2:]
    try:
        client(cmd, param)
    except RuntimeError as err:
        logger.error("ctl error: %s", err)
        sys.exit(1)


def client(cmd: str, args: List[str]):
    """Execute a command in the running step processor.

    The control protocol client allows a user scriptlet to execute
    the default handler for a step in the running application context,
    or set the value of a custom variable previously passed as an
    argument to :class:`craft_parts.LifecycleManager`.

    :param cmd: The function to execute in the step processor.
    :param args: Optional arguments.

    :raise RuntimeError: If the command is invalid.
    """
    if cmd not in ["pull", "build", "stage", "prime", "set"]:
        raise RuntimeError(f"invalid command {cmd!r}")

    try:
        call_fifo = os.environ["PARTS_CALL_FIFO"]
        feedback_fifo = os.environ["PARTS_FEEDBACK_FIFO"]
    except KeyError as err:
        raise RuntimeError(
            "{!s} environment variable must be defined.\nNote that this "
            "utility is designed for use only in part scriptlets.".format(err)
        ) from err

    data = {"function": cmd, "args": args}

    with open(call_fifo, "w") as fifo:
        fifo.write(json.dumps(data))

    with open(feedback_fifo, "r") as fifo:
        feedback = fifo.readline().strip()

    # Any feedback is considered a fatal error.
    if feedback:
        raise RuntimeError(feedback)
