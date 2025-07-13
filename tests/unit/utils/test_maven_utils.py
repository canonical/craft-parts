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
import logging
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
    GroupDict,
    MavenArtifact,
    MavenPlugin,
    MavenXMLError,
    _find_element,
    _get_available_version,
    _get_element_text,
    _get_existing_artifacts,
    _get_namespaces,
    _get_no_proxy_string,
    _get_poms,
    _insert_into_existing,
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
    artifacts = {
        MavenArtifact(
            artifact_id="package",
            group_id="org.starcraft",
            packaging_type="jar",
            version=version,
        )
        for version in package.get("package", set())
    }
    existing = {"org.starcraft": {"package": artifacts}}

    available = _get_available_version(
        existing,
        MavenArtifact("org.starcraft", "package", "1.0.0", packaging_type="jar"),
    )

    assert available is None or available in package["package"]


@dataclass(frozen=True)
class FakeArtifact(MavenArtifact):
    """Utility class for testing Maven artifacts"""

    group_id: str
    artifact_id: str
    version: str
    packaging_type: str | None = None

    def to_pom(self, repository: Path) -> Path:
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

        return pom_file


@pytest.mark.parametrize(
    ("artifacts"),
    [
        pytest.param(
            [
                FakeArtifact("org.starcraft", "test", "1.0.0"),
            ],
            id="simple",
        ),
        pytest.param(
            [
                FakeArtifact("org.starcraft", "test", "1.0.0"),
                FakeArtifact("org.notcraft", "is_even", "1.0.2"),
            ],
            id="multi-group",
        ),
        pytest.param(
            [
                FakeArtifact("org.starcraft", "test1", "1.0.0"),
                FakeArtifact("org.starcraft", "test2", "1.0.0"),
            ],
            id="multi-artifact",
        ),
        pytest.param(
            [
                FakeArtifact("org.starcraft", "test", "1.0.0"),
                FakeArtifact("org.starcraft", "test", "1.0.1"),
            ],
            id="multi-version",
        ),
    ],
)
def test_get_existing_artifacts(
    part_info: PartInfo, artifacts: list[FakeArtifact]
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

        assert any(a.version == artifact.version for a in art)


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


def test_maven_plugin_get_plugins() -> None:
    plugin1 = MavenArtifact(
        group_id="org.starcraft.plugins",
        artifact_id="plugin1",
        version="1.0.0",
        packaging_type="maven-plugin",
    )
    plugin2 = MavenArtifact(
        group_id="org.starcraft.plugins",
        artifact_id="plugin2",
        version="1.0.0",
        packaging_type="maven-plugin",
    )
    plugin3 = MavenArtifact(
        group_id="org.starcraft.mixed",
        artifact_id="plugin3",
        version="1.0.0",
        packaging_type="maven-plugin",
    )
    dep1 = MavenArtifact(
        group_id="org.starcraft.mixed",
        artifact_id="dep1",
        version="1.0.0",
        packaging_type="jar",
    )
    dep2 = MavenArtifact(
        group_id="org.starcraft.deps",
        artifact_id="dep2",
        version="1.0.0",
        packaging_type="jar",
    )
    dep3 = MavenArtifact(
        group_id="org.starcraft.deps",
        artifact_id="dep3",
        version="1.0.0",
        packaging_type="jar",
    )
    existing = {
        "org.starcraft.plugins": {
            plugin1.artifact_id: {plugin1},
            plugin2.artifact_id: {plugin2},
        },
        "org.starcraft.mixed": {
            plugin3.artifact_id: {plugin3},
            dep1.artifact_id: {dep1},
        },
        "org.starcraft.deps": {
            dep2.artifact_id: {dep2},
            dep3.artifact_id: {dep3},
        },
    }
    expected = {plugin1, plugin2, plugin3}

    assert MavenPlugin._get_existing_plugins(existing) == expected


def test_maven_plugin_set_remaining_plugins() -> None:
    remaining_plugins = [
        MavenArtifact(
            group_id="org.starcraft.plugins",
            artifact_id="plugin1",
            version="1.0.0",
            packaging_type="maven-plugin",
        ),
        MavenArtifact(
            group_id="org.starcraft.plugins",
            artifact_id="plugin2",
            version="1.0.0",
            packaging_type="maven-plugin",
        ),
    ]
    project = ET.fromstring(  # noqa: S314
        dedent("""\
        <project>
          <build>
          <foo>Don't delete me!</foo>
          </build>
        </project>""")
    )
    expected = dedent("""\
        <project>
          <build>
            <foo>Don't delete me!</foo>
            <pluginManagement>
              <plugins>
                <plugin>
                  <artifactId>plugin1</artifactId>
                  <groupId>org.starcraft.plugins</groupId>
                  <version>1.0.0</version>
                </plugin>
                <plugin>
                  <artifactId>plugin2</artifactId>
                  <groupId>org.starcraft.plugins</groupId>
                  <version>1.0.0</version>
                </plugin>
              </plugins>
            </pluginManagement>
          </build>
        </project>""")

    # Force remaining_plugins to be a list to keep its ordered property
    # This keeps the test reproducible
    MavenPlugin._set_remaining_plugins(remaining_plugins, project, {})  # type: ignore[reportArgumentType, arg-type]

    assert ET.tostring(project).decode(errors="replace") == expected


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

    base_artifact_params = {"group_id": "org.starcraft", "packaging_type": "jar"}
    existing = {
        "org.starcraft": {
            "test1": {
                MavenArtifact(
                    **base_artifact_params, artifact_id="test1", version="1.0.1"
                )
            },
            "test2": {
                MavenArtifact(
                    **base_artifact_params, artifact_id="test2", version="1.0.2"
                )
            },
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
              <!--Version updated by craft-parts from '1.0.0' to '1.0.1'-->
            </dependency>
            <dependency>
              <groupId>org.starcraft</groupId>
              <artifactId>test2</artifactId>
              <version>1.0.2</version>
              <!--Version updated by craft-parts from '1.0.0' to '1.0.2'-->
            </dependency>
          </dependencies>
        </project>""")


@pytest.mark.usefixtures("new_dir")
def test_update_pom_no_pom(part_info: PartInfo) -> None:
    with pytest.raises(MavenXMLError, match="does not exist"):
        update_pom(part_info=part_info, deploy_to=None, self_contained=False)


def create_project(part_info: PartInfo, project_xml: str) -> Path:
    part_info.part_build_subdir.mkdir(parents=True)
    pom_xml = part_info.part_build_subdir / "pom.xml"
    pom_xml.write_text(project_xml)

    return pom_xml


def test_update_pom_comment(part_info: PartInfo) -> None:
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

    update_pom(part_info=part_info, deploy_to=None, self_contained=False)

    expected_comment = "<!--This project was modified by craft-parts-->"
    assert expected_comment in pom_xml.read_text()


def test_update_pom_deploy_to(part_info: PartInfo) -> None:
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

    update_pom(
        part_info=part_info, deploy_to=part_info.part_export_dir, self_contained=False
    )

    # Make sure the distribution tag was added
    assert "<distributionManagement>" in pom_xml.read_text()
    # Make sure it is still valid XML
    ET.parse(pom_xml)  # noqa: S314


def test_update_pom_multiple_deploy_to(part_info: PartInfo) -> None:
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

    update_pom(
        part_info=part_info, deploy_to=part_info.part_export_dir, self_contained=False
    )

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
        update_pom(part_info=part_info, deploy_to=None, self_contained=True)

    mock_artifact.assert_called_once()
    mock_plugin.assert_called_once()
    mock_parent.assert_called_once()


@pytest.mark.parametrize(
    ("namespace", "expected"),
    [
        pytest.param("", {}, id="none"),
        pytest.param(
            'xmlns="https://example.com"', {"": "https://example.com"}, id="some"
        ),
    ],
)
def test_get_namespaces(namespace: str, expected: dict[str, str]) -> None:
    project = ET.fromstring(  # noqa: S314
        f"""
        <project {namespace}>
        </project>
    """
    )

    namespaces = _get_namespaces(project)

    assert namespaces == expected


def test_insert_into_existing(monkeypatch: pytest.MonkeyPatch, new_dir: Path) -> None:
    existing: GroupDict = GroupDict()
    test1 = MavenArtifact(
        group_id="org.starcraft",
        artifact_id="test1",
        version="1.0.0",
        packaging_type=None,
    )
    test2 = MavenArtifact(
        group_id="org.starcraft",
        artifact_id="test2",
        version="0.1.0",
        packaging_type=None,
    )
    test3_v1 = MavenArtifact(
        group_id="org.snarfcraft",
        artifact_id="test3",
        version="1.0.0",
        packaging_type=None,
    )
    test3_v2 = MavenArtifact(
        group_id="org.snarfcraft",
        artifact_id="test3",
        version="2.0.0",
        packaging_type=None,
    )
    artifacts = [test1, test2, test3_v1, test3_v2]

    # The mocking here bypasses the need to write a real pom to the disk, instead just
    # forcing the artifact to be returned from `from_pom`
    for artifact in artifacts:
        _insert_into_existing(existing, artifact)

    assert existing.get("org.starcraft") == {"test1": {test1}, "test2": {test2}}
    assert existing.get("org.snarfcraft") == {"test3": {test3_v1, test3_v2}}


def test_get_poms(part_info: PartInfo, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    existing: GroupDict = GroupDict()
    sentinel_art = MavenArtifact(
        group_id="org.starcraft",
        artifact_id="survivor",
        version="1.0.0",
        packaging_type=None,
    )
    _insert_into_existing(existing, sentinel_art)

    # Declare a project with three submodules
    # "single" will be a simple submodule with no children of its own
    # "nested" will have a submodule of its own
    # "idonotexist", well, doesn't exist
    top_art = """
        <project>
            <artifactId>top</artifactId>
            <groupId>org.starcraft</groupId>
            <version>1.0.0</version>

            <modules>
                <module>single</module>
                <module>nested</module>
                <module>idonotexist</module>
            </modules>
        </project>
    """
    single_art = """
        <project>
            <artifactId>single</artifactId>
            <groupId>org.starcraft</groupId>
            <version>1.0.0</version>
        </project>
    """
    nested_art = """
        <project>
            <artifactId>nested</artifactId>
            <groupId>org.starcraft</groupId>
            <version>1.0.0</version>

            <modules>
                <module>../egg</module>
            </modules>
        </project>
    """
    egg_art = """
        <project>
            <artifactId>egg</artifactId>
            <groupId>org.starcraft</groupId>
            <version>1.0.0</version>
        </project>
    """
    # An artifact that is not a submodule of anything and should not be discovered
    orphan_art = """
        <project>
            <artifactId>orphan</artifactId>
            <groupId>org.starcraft</groupId>
            <version>1.0.0</version>
        </project>
    """

    def _write_pom(art_name: str, art: str) -> Path:
        proj_dir = Path(part_info.part_build_subdir / art_name)
        proj_dir.mkdir(parents=True, exist_ok=True)
        pom = proj_dir / "pom.xml"
        pom.write_text(art)
        return pom

    top_pom = _write_pom(".", top_art)
    single_pom = _write_pom("single", single_art)
    nested_pom = _write_pom("nested", nested_art)
    egg_pom = _write_pom("egg", egg_art)
    _write_pom("orphan", orphan_art)

    poms = _get_poms(None, part_info, existing)

    assert sorted(poms) == sorted([top_pom, single_pom, nested_pom, egg_pom])
    expected_existing = {
        "org.starcraft": {
            "survivor": {sentinel_art},
            "single": {MavenArtifact.from_pom(single_pom)},
            "nested": {MavenArtifact.from_pom(nested_pom)},
            "egg": {MavenArtifact.from_pom(egg_pom)},
        }
    }
    assert existing == expected_existing
    assert (
        "Discovered poms for part 'my-part': [pom.xml, single/pom.xml, nested/pom.xml, egg/pom.xml]"
        in caplog.text
    )
    assert (
        "The pom 'pom.xml' declares a submodule at 'idonotexist', but this submodule could not be found."
        in caplog.text
    )


def test_update_pom_file(part_info: PartInfo, tmp_path: Path) -> None:
    project_xml = dedent("""\
        <project>
            <groupId>org.starcraft</groupId>
            <artifactId>test1</artifactId>
            <version>1.0.0</version>
        </project>
    """)

    root_pom = create_project(part_info, project_xml)
    new_pom = part_info.part_build_subdir / "artifact.pom"
    new_pom.write_text(project_xml)

    deploy_to = tmp_path / "deploy"
    update_pom(
        part_info=part_info, deploy_to=deploy_to, self_contained=False, pom_file=new_pom
    )

    # Check that the root xml file is untouched
    assert root_pom.read_text() == project_xml

    # Check that the pom file passed as parameter is updated
    expected_repo = f"file://{deploy_to}"
    assert expected_repo in new_pom.read_text()
