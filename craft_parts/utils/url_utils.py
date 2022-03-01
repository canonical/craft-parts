# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

"""URL parsing and downloading helpers."""

import logging
import os
import urllib.parse
import urllib.request
from typing import Optional

from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


def get_url_scheme(url: str) -> str:
    """Return the given URL's scheme."""
    return urllib.parse.urlparse(url).scheme


def is_url(url: str) -> bool:
    """Verify whether the given string is a valid URL."""
    return get_url_scheme(url) != ""


def download_request(
    request, destination: str, message: Optional[str] = None, total_read: int = 0
):
    """Download a request with nice progress bars.

    :param request: The URL download request.
    :param destination: The destination file name.
    :param message: The message shown in the progress bar.
    """
    # Doing len(request.content) may defeat the purpose of a
    # progress bar
    total_length = 0
    if not request.headers.get("Content-Encoding", ""):
        total_length = int(request.headers.get("Content-Length", "0"))
        # Content-Length in the case of resuming will be
        # Content-Length - total_read so we add back up to have the feel of
        # resuming
        if os.path.exists(destination):
            total_length += total_read

    if message:
        logger.debug(message)
    else:
        logger.debug("Downloading %r", destination)

    # FIXME: re-impement progress bar support when messages to user support is ready
    # progress_bar = _init_progress_bar(total_length, destination, message)
    # progress_bar.start()

    if os.path.exists(destination):
        mode = "ab"
    else:
        mode = "wb"
    with open(destination, mode) as destination_file:
        for buf in request.iter_content(1024):
            destination_file.write(buf)
            if not os_utils.is_dumb_terminal():
                total_read += len(buf)
                # progress_bar.update(total_read)
    # progress_bar.finish()
