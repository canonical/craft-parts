# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

from pathlib import Path

import pytest
import requests
from craft_parts.utils import url_utils


@pytest.mark.parametrize(
    ("url", "result"),
    [
        ("", ""),
        ("not an url", ""),
        ("/stll/not/an/url", ""),
        ("scheme://some/location", "scheme"),
    ],
)
def test_get_url_scheme(url, result):
    assert url_utils.get_url_scheme(url) == result


@pytest.mark.parametrize(
    ("url", "result"),
    [
        ("", False),
        ("not an url", False),
        ("/stll/not/an/url", False),
        ("scheme://some/location", True),
    ],
)
def test_is_url(url, result):
    assert url_utils.is_url(url) == result


@pytest.mark.usefixtures("new_dir")
def test_download_request(requests_mock):
    source_url = "http://test.com/source"
    requests_mock.get(source_url, text="content")

    test_file = Path("test_file")

    request = requests.get(source_url, stream=True, timeout=3600)
    url_utils.download_request(request, "test_file")

    assert test_file.is_file()
    assert test_file.read_bytes() == b"content"
