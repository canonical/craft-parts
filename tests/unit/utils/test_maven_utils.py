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
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import cast
from unittest import mock

import pytest
from craft_parts import Part
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.utils.maven.common import (
    MavenArtifact,
    MavenPlugin,
    MavenXMLError,
    _find_element,
    _get_available_version,
    _get_element_text,
    _get_existing_artifacts,
    _get_no_proxy_string,
    _needs_proxy_config,
    _set_version,
    create_maven_settings,
    update_pom,
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
    backstage = cast("Path", part_info.backstage_dir) / "maven-use"
    backstage.mkdir(parents=True)
    if set_mirror:
        set_mirror_content = dedent(
            """\
            <mirrors>
                <mirror>
                <id>debian</id>
                <mirrorOf>central</mirrorOf>
                <name>Mirror Repository from Debian packages</name>
                <url>file:///usr/share/maven-repo</url>
                </mirror>
            </mirrors>
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
            {set_mirror_content}
            <localRepository>{part_info.part_build_subdir / ".parts/.m2/repository"}</localRepository>
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

    expected_error = dedent("""\
        Could not find path 'nope' in element 'foo'
        Could not find path 'nope' in the following XML element:
        <foo>
          <bar>Howdy!</bar>
        </foo>""")
    with pytest.raises(MavenXMLError, match=expected_error):
        _find_element(element, "nope", {})


def test_get_element_text() -> None:
    element = ET.fromstring("<bar>Howdy!</bar>")  # noqa: S314

    assert _get_element_text(element) == "Howdy!"

    element = ET.fromstring("<foo><bar>Howdy!</bar></foo>")  # noqa: S314

    expected_error = dedent("""\
        No text field found on 'foo'
        No text field found on 'foo' in the following XML element:
        <foo>
          <bar>Howdy!</bar>
        </foo>""")
    with pytest.raises(MavenXMLError, match=expected_error):
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
    ("package"),
    [
        pytest.param({}, id="not-available"),
        pytest.param({"package": {"1.0.1"}}, id="upgrade"),
        pytest.param({"package": {"1.0.1", "1.0.2"}}, id="multi"),
    ],
)
def test_get_available_version(package: dict[str, set[str]]) -> None:
    existing = {"org.starcraft": package}

    available = _get_available_version(
        existing, MavenArtifact("org.starcraft", "package", "1.0.0")
    )

    assert available is None or available in package["package"]


@dataclass
class TestArtifact:
    """Utility class for testing `_get_existing_artifacts`."""

    group_id: str
    artifact_id: str
    version: str

    def to_pom(self, repository: Path):
        pom_template = """\
        <project>
          <modelVersion>4.0.0</modelVersion>
          <groupId>{group}</groupId>
          <artifactId>{artifact}</artifactId>
          <version>{version}</version>
        </project>
        """

        pom_dir = repository / (self.group_id.replace(".", "/")) / self.version
        pom_dir.mkdir(parents=True, exist_ok=True)

        pom_file = pom_dir / f"{self.artifact_id}.pom"
        pom_file.write_text(
            pom_template.format(
                group=self.group_id, artifact=self.artifact_id, version=self.version
            )
        )


@pytest.mark.parametrize(
    ("artifacts"),
    [
        pytest.param(
            [
                TestArtifact("org.starcraft", "test", "1.0.0"),
            ],
            id="simple",
        ),
        pytest.param(
            [
                TestArtifact("org.starcraft", "test", "1.0.0"),
                TestArtifact("org.notcraft", "is_even", "1.0.2"),
            ],
            id="multi-group",
        ),
        pytest.param(
            [
                TestArtifact("org.starcraft", "test1", "1.0.0"),
                TestArtifact("org.starcraft", "test2", "1.0.0"),
            ],
            id="multi-artifact",
        ),
        pytest.param(
            [
                TestArtifact("org.starcraft", "test", "1.0.0"),
                TestArtifact("org.starcraft", "test", "1.0.1"),
            ],
            id="multi-version",
        ),
    ],
)
def test_get_existing_artifacts(
    part_info: PartInfo, artifacts: list[TestArtifact]
) -> None:
    backstage = cast("Path", part_info.backstage_dir) / "maven-use"
    backstage.mkdir(parents=True)

    # Generate a test backstage directory
    for artifact in artifacts:
        artifact.to_pom(backstage)

    result = _get_existing_artifacts(part_info)

    # Validate contents of the discovered packages
    for artifact in artifacts:
        group = result.get(artifact.group_id)
        assert group is not None

        art = group.get(artifact.artifact_id)
        assert art is not None

        assert artifact.version in art


def test_maven_artifact_from_element() -> None:
    element = ET.fromstring("""\
        <dependency>
            <groupId>org.starcraft</groupId>
            <artifactId>test</artifactId>
            <version>X.Y.Z</version>
        </dependency>
        """)  # noqa: S314

    art = MavenArtifact.from_element(element, {})

    assert art.group_id == "org.starcraft"
    assert art.artifact_id == "test"
    assert art.version == "X.Y.Z"


def test_maven_artifact_from_element_no_version() -> None:
    element = ET.fromstring("""\
        <dependency>
            <groupId>org.starcraft</groupId>
            <artifactId>test</artifactId>
        </dependency>
        """)  # noqa: S314

    art = MavenArtifact.from_element(element, {})

    assert art.group_id == "org.starcraft"
    assert art.artifact_id == "test"
    assert art.version is None


def test_maven_plugin_from_element_no_group() -> None:
    element = ET.fromstring("""\
        <dependency>
            <artifactId>test</artifactId>
            <version>X.Y.Z</version>
        </dependency>
        """)  # noqa: S314

    plugin = MavenPlugin.from_element(element, {})

    assert plugin.group_id == "org.apache.maven.plugins"
    assert plugin.artifact_id == "test"
    assert plugin.version == "X.Y.Z"


def test_maven_artifact_from_pom(tmp_path: Path) -> None:
    pom = """\
        <project>
          <modelVersion>4.0.0</modelVersion>
          <groupId>org.starcraft</groupId>
          <artifactId>test</artifactId>
          <version>X.Y.Z</version>
        </project>
    """
    pom_file = tmp_path / "test.pom"
    pom_file.write_text(pom)

    art = MavenArtifact.from_pom(pom_file)

    assert art.group_id == "org.starcraft"
    assert art.artifact_id == "test"
    assert art.version == "X.Y.Z"


def test_maven_artifact_update_versions() -> None:
    project_xml = dedent("""\
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test1</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test2</artifactId>
                    <version>1.0.0</version>
                </dependency>
            </dependencies>
        </project>
    """)
    project = ET.fromstring(project_xml)  # noqa: S314

    existing = {
        "org.starcraft": {
            "test1": {"1.0.1"},
            "test2": {"1.0.2"},
        }
    }

    MavenArtifact.update_versions(project, {}, existing)

    assert ET.tostring(project).decode("utf8") == dedent("""\
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test1</artifactId>
                    <version>1.0.1</version>
                <!--Version updated by craft-parts from '1.0.0' to '1.0.1'--></dependency>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test2</artifactId>
                    <version>1.0.2</version>
                <!--Version updated by craft-parts from '1.0.0' to '1.0.2'--></dependency>
            </dependencies>
        </project>""")


@pytest.mark.usefixtures("new_dir")
def test_update_pom_no_pom(part_info: PartInfo) -> None:
    with pytest.raises(MavenXMLError, match="does not exist"):
        update_pom(part_info=part_info, add_distribution=False, self_contained=False)


def create_project(part_info: PartInfo, project_xml: str) -> Path:
    part_info.part_build_subdir.mkdir(parents=True)
    pom_xml = part_info.part_build_subdir / "pom.xml"
    pom_xml.write_text(project_xml)

    return pom_xml


def test_update_pom_add_distribution(part_info: PartInfo) -> None:
    project_xml = dedent("""\
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test1</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test2</artifactId>
                    <version>1.0.0</version>
                </dependency>
            </dependencies>
        </project>
    """)

    pom_xml = create_project(part_info, project_xml)

    update_pom(part_info=part_info, add_distribution=True, self_contained=False)

    # Make sure the distribution tag was added
    assert "<distributionManagement>" in pom_xml.read_text()
    # Make sure it is still valid XML
    ET.parse(pom_xml)  # noqa: S314


def test_update_pom_multiple_add_distribution(part_info: PartInfo) -> None:
    """Make sure that pre-existing distributionManagement tags are overwritten."""

    project_xml = dedent("""\
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test1</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test2</artifactId>
                    <version>1.0.0</version>
                </dependency>
            </dependencies>

            <distributionManagement>foo</distributionManagement>
        </project>
    """)

    pom_xml = create_project(part_info, project_xml)

    update_pom(part_info=part_info, add_distribution=True, self_contained=False)

    pom_xml_contents = pom_xml.read_text()
    # Only one distributionManagement tag is present
    assert pom_xml_contents.count("<distributionManagement>") == 1
    # The old distributionManagement is gone
    assert "foo" not in pom_xml_contents
    # It is still valid XML
    tree = ET.parse(pom_xml)  # noqa: S314

    # The new distributionManagement is in place
    project = tree.getroot()
    distro_element = cast("ET.Element", project.find("distributionManagement"))
    distro_repo = distro_element.find("repository")
    assert distro_repo is not None
    distro_id = distro_repo.find("id")
    assert distro_id is not None
    assert distro_id.text == "craft"


def test_update_pom_self_contained(part_info: PartInfo) -> None:
    project_xml = dedent("""\
        <project>
            <dependencies>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test1</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.starcraft</groupId>
                    <artifactId>test2</artifactId>
                    <version>1.0.0</version>
                </dependency>
            </dependencies>
        </project>
    """)

    create_project(part_info, project_xml)

    with (
        mock.patch(
            "craft_parts.utils.maven.common.MavenArtifact.update_versions"
        ) as mock_artifact,
        mock.patch(
            "craft_parts.utils.maven.common.MavenPlugin.update_versions"
        ) as mock_plugin,
        mock.patch(
            "craft_parts.utils.maven.common.MavenParent.update_versions"
        ) as mock_parent,
    ):
        update_pom(part_info=part_info, add_distribution=False, self_contained=True)

    mock_artifact.assert_called_once()
    mock_plugin.assert_called_once()
    mock_parent.assert_called_once()
