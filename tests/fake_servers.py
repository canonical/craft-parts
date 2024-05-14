# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""Request handlers for the http_server fixture."""

import http.server
import logging

logger = logging.getLogger(__name__)


class BaseHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """The base class for the http server request handlers."""

    def log_message(self, *args, **kwargs) -> None:
        logger.debug(args, **kwargs)

    def raise_not_implemented(self, path):
        logger.error("Not implemented %s in server: %s", path, self.__class__.__name__)
        raise NotImplementedError(path)


class DummyHTTPRequestHandler(BaseHTTPRequestHandler):
    """A request handler that does nothing."""

    def do_GET(self):  # noqa: N802
        pass


class FakeFileHTTPRequestHandler(BaseHTTPRequestHandler):
    """Serve a fake file."""

    def do_GET(self):  # noqa: N802
        if self.path.endswith("404-not-found"):
            self.send_response(404)
            self.end_headers()
        else:
            data = "Test fake file"
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(data.encode())
