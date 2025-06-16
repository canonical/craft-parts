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

import io
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from textwrap import dedent
from unittest import mock

import pytest
from craft_parts import Part
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.utils.maven.common import (
    _get_no_proxy_string,
    _needs_proxy_config,
    create_maven_settings,
)


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


@pytest.fixture
def part_info(new_dir: Path) -> PartInfo:
    cache_dir = new_dir / "cache"
    cache_dir.mkdir()
    return PartInfo(
        project_info=ProjectInfo(
            application_name="testcraft",
            cache_dir=cache_dir,
        ),
        part=Part("my-part", {}),
    )


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param({}, "localhost", id="empty"),
        pytest.param(
            {"no_proxy": "https://canonical.com"}, "https://canonical.com", id="single"
        ),
        pytest.param(
            {"no_proxy": "https://canonical.com, https://launchpad.net"},
            "https://canonical.com|https://launchpad.net",
            id="multiple",
        ),
    ],
)
def test_get_no_proxy_string(env: dict[str, str], expected: str) -> None:
    with mock.patch.dict(os.environ, env):
        assert _get_no_proxy_string() == expected


def test_create_settings_no_change(
    part_info: PartInfo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "craft_parts.utils.maven.common._needs_proxy_config", lambda: False
    )

    # Ensure no path is returned
    assert create_maven_settings(part_info=part_info, set_mirror=False) is None
    # Ensure that the settings file was not made
    assert not (part_info.part_build_subdir / ".parts/.m2/settings.xml").is_file()


def _normalize_settings(settings):
    with io.StringIO(settings) as f:
        tree = ET.parse(f)  # noqa: S314
    for element in tree.iter():
        if element.text is not None and element.text.isspace():
            element.text = None
        if element.tail is not None and element.tail.isspace():
            element.tail = None
    with io.StringIO() as f:
        tree.write(
            f,
            encoding="unicode",
            default_namespace="http://maven.apache.org/SETTINGS/1.0.0",
        )
        return f.getvalue() + "\n"


@pytest.mark.parametrize(
    ("protocol", "expected_protocol"),
    [
        pytest.param("http_proxy", "http", id="http"),
        pytest.param("HTTP_PROXY", "http", id="HTTP"),
        pytest.param("https_proxy", "https", id="https"),
        pytest.param("HTTPS_PROXY", "https", id="HTTPS"),
    ],
)
@pytest.mark.parametrize(
    ("no_proxy", "non_proxy_hosts"),
    [(None, "localhost"), ("foo", "foo"), ("foo,bar", "foo|bar")],
)
@pytest.mark.parametrize(
    ("credentials", "credentials_xml"),
    [
        pytest.param(
            "username:hunter7@",
            "<username>username</username>\n<password>hunter7</password>\n",
            id="with-creds",
        ),
        pytest.param("", "", id="no-creds"),
    ],
)
def test_settings_proxy(
    part_info: PartInfo,
    protocol: str,
    expected_protocol: str,
    no_proxy: str | None,
    non_proxy_hosts: str,
    credentials: str,
    credentials_xml: str,
):
    settings_path = Path(
        part_info._dirs.parts_dir / "my-part/build/.parts/.m2/settings.xml"
    )

    expected_content = dedent(
        f"""\
        <settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 http://maven.apache.org/xsd/settings-1.0.0.xsd">
          <interactiveMode>false</interactiveMode>
          <proxies>
            <proxy>
              <id>{expected_protocol}_proxy</id>
              <protocol>{expected_protocol}</protocol>
              <host>my-proxy-host</host>
              <port>3128</port>
              <nonProxyHosts>{non_proxy_hosts}</nonProxyHosts>
              {credentials_xml}
              <active>true</active>
            </proxy>
          </proxies>
        </settings>
        """
    )

    env_dict = {
        protocol: f"http://{credentials}my-proxy-host:3128",
    }
    if no_proxy:
        env_dict["no_proxy"] = no_proxy

    with mock.patch.dict(os.environ, env_dict):
        create_maven_settings(part_info=part_info, set_mirror=False)
        assert settings_path.exists()
        assert _normalize_settings(settings_path.read_text()) == _normalize_settings(
            expected_content
        )
