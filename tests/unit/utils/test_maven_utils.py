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
from typing import cast
from unittest import mock

import pytest
from craft_parts import Part
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.utils.maven.common import (
    MavenArtifact,
    MavenXMLError,
    _find_element,
    _get_available_version,
    _get_element_text,
    _get_no_proxy_string,
    _needs_proxy_config,
    _set_version,
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


@pytest.fixture
def settings_path(part_info: PartInfo) -> Path:
    return part_info.part_build_subdir / ".parts/.m2/settings.xml"


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
    part_info: PartInfo, settings_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "craft_parts.utils.maven.common._needs_proxy_config", lambda: False
    )

    # Ensure no path is returned
    assert create_maven_settings(part_info=part_info, set_mirror=False) is None
    # Ensure that the settings file was not made
    assert not settings_path.is_file()


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
@pytest.mark.parametrize(
    ("set_mirror"),
    [pytest.param(True, id="mirror"), pytest.param(False, id="no-mirror")],
)
def test_create_settings(
    part_info: PartInfo,
    settings_path: Path,
    protocol: str,
    expected_protocol: str,
    no_proxy: str | None,
    non_proxy_hosts: str,
    credentials: str,
    credentials_xml: str,
    *,
    set_mirror: bool,
):
    if set_mirror:
        backstage = cast("Path", part_info.backstage_dir) / "maven-use"
        backstage.mkdir(parents=True)
        set_mirror_content = dedent(
            f"""\
            <profiles>
                <profile>
                <id>craft</id>
                <repositories>
                    <repository>
                        <id>craft</id>
                        <name>Craft-managed intermediate repository</name>
                        <url>{backstage.as_uri()}</url>
                    </repository>
                </repositories>
                </profile>
            </profiles>
            <activeProfiles>
                <activeProfile>craft</activeProfile>
            </activeProfiles>
            <mirrors>
                <mirror>
                <id>debian</id>
                <mirrorOf>central</mirrorOf>
                <name>Mirror Repository from Debian packages</name>
                <url>file:///usr/share/maven-repo</url>
                </mirror>
            </mirrors>
            <localRepository>{part_info.part_build_subdir / ".parts/.m2/repository"}</localRepository>
            """
        )
    else:
        set_mirror_content = ""

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
          {set_mirror_content}
        </settings>
        """
    )

    env_dict = {
        protocol: f"http://{credentials}my-proxy-host:3128",
    }
    if no_proxy:
        env_dict["no_proxy"] = no_proxy

    with mock.patch.dict(os.environ, env_dict):
        create_maven_settings(part_info=part_info, set_mirror=set_mirror)
        assert settings_path.exists()
        assert _normalize_settings(settings_path.read_text()) == _normalize_settings(
            expected_content
        )


def test_find_element() -> None:
    element = ET.fromstring("<foo><bar>Howdy!</bar></foo>")  # noqa: S314

    find_result = _find_element(element, "bar", {})
    assert find_result is not None
    assert find_result.text == "Howdy!"

    with pytest.raises(MavenXMLError, match="Could not parse"):
        _find_element(element, "nope", {})


def test_get_element_text() -> None:
    element = ET.fromstring("<bar>Howdy!</bar>")  # noqa: S314

    assert _get_element_text(element) == "Howdy!"

    element = ET.fromstring("<foo><bar>Howdy!</bar></foo>")  # noqa: S314

    with pytest.raises(MavenXMLError, match="No text field"):
        _get_element_text(element)


def test_set_version_upgrade() -> None:
    dependency = """\
        <dependency>
            <groupId>org.starcraft</groupId>
            <artifactId>test</artifactId>
            <version>1.0.0</version>
        </dependency>
    """

    dep_element = ET.fromstring(dependency)  # noqa: S314

    _set_version(dep_element, {}, "1.0.1")

    version = _find_element(dep_element, "version", {})
    assert _get_element_text(version) == "1.0.1"

    assert b"Version updated by craft-parts from '1.0.0' to '1.0.1'" in ET.tostring(
        dep_element
    )


def test_set_version_unpinned() -> None:
    dependency = """\
        <dependency>
            <groupId>org.starcraft</groupId>
            <artifactId>test</artifactId>
        </dependency>
    """

    dep_element = ET.fromstring(dependency)  # noqa: S314

    _set_version(dep_element, {}, "1.0.1")

    version = _find_element(dep_element, "version", {})
    assert _get_element_text(version) == "1.0.1"

    assert b"Version set by craft-parts to '1.0.1'" in ET.tostring(dep_element)


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        pytest.param({}, None, id="not-available"),
        pytest.param({"package": {"1.0.1"}}, "1.0.1", id="upgrade"),
        pytest.param({"package": {"1.0.1", "1.0.2"}}, "1.0.1", id="multi"),
    ],
)
def test_get_available_version(
    package: dict[str, set[str]], expected: str | None
) -> None:
    existing = {"org.starcraft": package}

    assert (
        _get_available_version(
            existing, MavenArtifact("org.starcraft", "package", "1.0.0")
        )
        is expected
    )
