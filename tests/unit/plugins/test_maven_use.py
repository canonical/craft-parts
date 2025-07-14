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

"""Unit tests for the Maven use plugin."""

import re
from pathlib import Path
from textwrap import dedent

import pytest
from craft_parts import errors
from craft_parts.infos import PartInfo
from craft_parts.plugins.maven_use_plugin import MavenUsePlugin


@pytest.fixture
def fake_project_dir(new_dir: Path) -> Path:
    project_dir = new_dir / Path("cargo-project")
    project_dir.mkdir(parents=True, exist_ok=False)
    return project_dir


@pytest.fixture
def project_name() -> str:
    return "craft-parts"


@pytest.fixture
def project_version() -> str:
    return "0.0.1"


@pytest.fixture
def fake_maven_project(
    part_info: PartInfo, project_name: str, project_version: str
) -> Path:
    part_info.part_build_subdir.mkdir(parents=True)
    project_file = part_info.part_build_subdir / "pom.xml"
    project_file.write_text(
        dedent(
            f"""\
            <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
                <modelVersion>4.0.0</modelVersion>

                <groupId>com.starcraft</groupId>
                <packaging>jar</packaging>
                <artifactId>{project_name}</artifactId>
                <version>{project_version}</version>

                <properties>
                    <maven.compiler.source>1.8</maven.compiler.source>
                    <maven.compiler.target>1.8</maven.compiler.target>
                </properties>
            </project>
            """
        )
    )

    return project_file


@pytest.fixture
def plugin(part_info: PartInfo) -> MavenUsePlugin:
    properties = MavenUsePlugin.properties_class.unmarshal({"source": "."})
    return MavenUsePlugin(properties=properties, part_info=part_info)


def test_get_build_snaps(plugin: MavenUsePlugin) -> None:
    assert plugin.get_build_snaps() == set()


def test_get_build_packages(plugin: MavenUsePlugin) -> None:
    assert plugin.get_build_packages() == set()


# Note - test_get_build_environment is intentionally not tested as it is
# inherited from the Java plugin and is tested there already


@pytest.mark.parametrize(
    ("create_mvnw"),
    [True, False],
    ids=["mvnw", "mvn"],
)
@pytest.mark.usefixtures("fake_maven_project")
def test_get_build_commands(
    plugin: MavenUsePlugin, maven_settings_path: Path, *, create_mvnw: bool
) -> None:
    if create_mvnw:
        (plugin._part_info.part_build_subdir / "mvnw").touch()

    assert plugin.get_build_commands() == [
        f"{plugin._maven_executable} deploy -s {maven_settings_path}"
    ]


def test_get_build_commands_is_reentrant(
    plugin: MavenUsePlugin, fake_maven_project: Path
) -> None:
    """Make sure a new pom is always written."""
    initial_age = fake_maven_project.stat().st_mtime

    plugin.get_build_commands()

    assert fake_maven_project.stat().st_mtime > initial_age


@pytest.mark.parametrize(
    ("create_mvnw"),
    [True, False],
    ids=["mvnw", "mvn"],
)
def test_get_maven_executable(plugin: MavenUsePlugin, *, create_mvnw: bool) -> None:
    if create_mvnw:
        plugin._part_info.part_build_subdir.mkdir(parents=True, exist_ok=False)
        mvnw = plugin._part_info.part_build_subdir / "mvnw"
        mvnw.touch()
        expected = str(mvnw)
    else:
        expected = "mvn"

    assert plugin._maven_executable == expected


@pytest.mark.usefixtures("set_self_contained")
def test_bad_dependency(plugin: MavenUsePlugin) -> None:
    plugin._part_info.part_build_subdir.mkdir(parents=True)
    pom = plugin._part_info.part_build_subdir / "pom.xml"
    pom.write_text("""
        <project>
            <dependencies>
                <dependency>
                </dependency>
            </dependencies>
        </project>
    """)

    err_re = re.compile(
        r"Plugin configuration failed for part my-part:.*Check that the 'pom\.xml' file is valid\.",
        flags=re.DOTALL,
    )
    with pytest.raises(errors.PartsError, match=err_re):
        plugin.get_build_commands()


def test_get_build_commands_from_binaries(plugin: MavenUsePlugin) -> None:
    project_xml = dedent("""\
        <project>
            <groupId>org.starcraft</groupId>
            <artifactId>test1</artifactId>
            <version>1.0.0</version>
        </project>
    """)
    maven_use_dir = plugin._part_info.part_build_subdir / "maven-use"
    maven_use_dir.mkdir(parents=True)
    fake_pom = maven_use_dir / "fake.pom"
    fake_pom.write_text(project_xml)

    build_commands = plugin.get_build_commands()

    # Check that the list build commands is just a copy (like the dump plugin)
    export_dir = plugin._part_info.part_export_dir
    assert build_commands == [
        f'cp --archive --link --no-dereference ./maven-use "{export_dir}"'
    ]

    # Check that the pom file in the "maven-use/" directory was updated
    assert "This project was modified by craft-parts" in fake_pom.read_text()
