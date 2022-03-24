# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2022 Canonical Ltd.
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
from typing import List, Optional

logger = logging.getLogger(__name__)


class CraftCtl:
    """Client for the craft-parts ctl protocol.

    Craftctl is used to execute built-in step handlers and to get and set
    variables in the running parts processor context.
    """

    @classmethod
    def run(cls, cmd: str, args: List[str]) -> Optional[str]:
        """Handle craftctl commands.

        :param cmd: The command to handle.
        :param args: Command arguments.

        :raises RuntimeError: If the command is not handled.
        """
        if cmd in ["default", "set"]:
            _client(cmd, args)
            return None

        if cmd in "get":
            retval = _client(cmd, args)
            return retval

        raise RuntimeError(f"invalid command {cmd!r}")


def _client(cmd: str, args: List[str]):
    """Execute a command in the running step processor.

    The control protocol client allows a user scriptlet to execute
    the default handler for a step in the running application context,
    or set the value of a custom variable previously passed as an
    argument to :class:`craft_parts.LifecycleManager`.

    :param cmd: The command to execute in the step processor.
    :param args: Optional arguments.

    :raise RuntimeError: If the command is invalid.
    """
    try:
        call_fifo = os.environ["PARTS_CALL_FIFO"]
        feedback_fifo = os.environ["PARTS_FEEDBACK_FIFO"]
    except KeyError as err:
        raise RuntimeError(
            f"{err!s} environment variable must be defined.\nNote that this "
            f"utility is designed for use only in part scriptlets."
        ) from err

    data = {"function": cmd, "args": args}

    with open(call_fifo, "w") as fifo:
        fifo.write(json.dumps(data))

    with open(feedback_fifo, "r") as fifo:
        feedback = fifo.readline().split(" ", 1)

    # response from server is in the form "<status> <message>" where
    # <status> can be either "OK" or "ERR".  Previous server versions
    # used an empty response as success, anything else was an error
    # message.

    status = feedback[0]
    message = feedback[1].strip() if len(feedback) > 1 else ""
    retval = None

    if status == "OK":
        # command has succeeded
        retval = message
    elif status == "ERR":
        # command has failed
        raise RuntimeError(message)

    return retval


def main():
    """Run the ctl client cli."""
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <command> [arguments]")
        sys.exit(1)

    cmd, args = sys.argv[1], sys.argv[2:]
    try:
        ret = CraftCtl.run(cmd, args)
        if ret:
            print(ret)
    except RuntimeError as err:
        logger.error("error: %s", err)
        sys.exit(1)
