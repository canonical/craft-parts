# Copyright 2025 Canonical Ltd.
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

"""Unit tests for the Maven plugin utilities."""

import os
from unittest import mock

import pytest
from craft_parts.utils.maven.common import _needs_proxy_config


@pytest.mark.parametrize(
    ("proxy_var", "expected"),
    [
        pytest.param("http_proxy", True, id="http_proxy"),
        pytest.param("https_proxy", True, id="https_proxy"),
        pytest.param("HTTP_PROXY", True, id="HTTP_PROXY"),
        pytest.param("HTTPS_PROXY", True, id="HTTPS_PROXY"),
        pytest.param("SOME_OTHER_PROXY", False, id="other_proxy"),
        pytest.param("IM_HERE_TOO", False, id="not_a_proxy"),
    ],
)
def test_needs_proxy_config(proxy_var: str, *, expected: bool) -> None:
    with mock.patch.dict(os.environ, {proxy_var: "foo"}):
        assert _needs_proxy_config() == expected
