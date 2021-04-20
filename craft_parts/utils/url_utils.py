# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

"""URL parsing and downloading helpers."""

import os
import urllib.parse
import urllib.request

# TODO:stdmsg: refactor to use the standard message library once available
import progressbar  # type: ignore

from craft_parts.utils import os_utils


def get_url_scheme(url: str) -> str:
    """Return the given URL's scheme."""
    return urllib.parse.urlparse(url).scheme


def is_url(url: str) -> bool:
    """Verify whether the given string is a valid URL."""
    return get_url_scheme(url) != ""


def download_request(
    request, destination: str, message: str = None, total_read: int = 0
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

    progress_bar = _init_progress_bar(total_length, destination, message)
    progress_bar.start()

    if os.path.exists(destination):
        mode = "ab"
    else:
        mode = "wb"
    with open(destination, mode) as destination_file:
        for buf in request.iter_content(1024):
            destination_file.write(buf)
            if not os_utils.is_dumb_terminal():
                total_read += len(buf)
                progress_bar.update(total_read)
    progress_bar.finish()


def download_ftp(uri, destination, message=None):
    """Download from the given URI.

    :param uri: the URI to download from.
    :param destination: the file to download to."
    :param message: the progress bar message."
    """
    _UrllibDownloader(uri, destination, message).download()


def _init_progress_bar(
    total_length: int, destination: str, message=None
) -> progressbar.ProgressBar:
    if not message:
        message = "Downloading {!r}".format(os.path.basename(destination))

    valid_length = total_length and total_length > 0
    dumb_terminal = os_utils.is_dumb_terminal()

    if valid_length and dumb_terminal:
        widgets = [message, " ", progressbar.Percentage()]
        maxval = total_length
    elif valid_length and not dumb_terminal:
        widgets = [
            message,
            progressbar.Bar(marker="=", left="[", right="]"),
            " ",
            progressbar.Percentage(),
        ]
        maxval = total_length
    elif not valid_length and dumb_terminal:
        widgets = [message]
        maxval = progressbar.UnknownLength
    else:
        widgets = [message, progressbar.AnimatedMarker()]
        maxval = progressbar.UnknownLength

    return progressbar.ProgressBar(widgets=widgets, maxval=maxval)


# XXX: maybe refactor to use ftplib
class _UrllibDownloader:
    """Download an URI with nice progress bars."""

    def __init__(self, uri, destination, message=None):
        self.uri = uri
        self.destination = destination
        self.message = message
        self.progress_bar = None

    def download(self):
        """Download from this URL."""
        urllib.request.urlretrieve(self.uri, self.destination, self._progress_callback)

        if self.progress_bar:
            self.progress_bar.finish()

    # TODO:stdmsg: use a standard ui progress bar instead
    def _progress_callback(self, block_num, block_size, total_length):
        if not self.progress_bar:
            self.progress_bar = _init_progress_bar(
                total_length, self.destination, self.message
            )
            self.progress_bar.start()

        total_read = block_num * block_size
        self.progress_bar.update(
            min(total_read, total_length) if total_length > 0 else total_read
        )
