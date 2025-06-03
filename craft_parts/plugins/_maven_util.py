# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
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

"""Utilities for Maven projects and settings."""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from craft_parts import errors, infos
from craft_parts.plugins._maven_xml import (
    CRAFT_REPO_TEMPLATE,
    DISTRIBUTION_REPO_TEMPLATE,
    LOCAL_REPO_TEMPLATE,
    MIRROR_REPO,
    SETTINGS_TEMPLATE,
)

logger = logging.getLogger(__name__)


def create_maven_settings(*, part_info: infos.PartInfo, set_mirror: bool) -> Path:
    """Create a Maven configuration file.

    The settings file contains additional configuration for Maven, such
    as proxy parameters.

    :param settings_path: the location the settings file will be created.
    """
    settings_path = part_info.part_build_subdir / ".parts/.m2/settings.xml"
    local_repo = part_info.part_build_subdir / ".parts/.m2/repository"
    backstage_repo = part_info.backstage_dir / "maven-use"

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # This is the local repository used by maven to store downloaded & generated
    # artifacts
    local_element = LOCAL_REPO_TEMPLATE.format(repo_dir=local_repo)

    craft_element = ""
    if backstage_repo.is_dir():
        # This is the shared repository in the backstage
        craft_element = CRAFT_REPO_TEMPLATE.format(repo_uri=backstage_repo.as_uri())

    mirror_element = ""
    if set_mirror:
        mirror_element = MIRROR_REPO

    settings_xml = SETTINGS_TEMPLATE.format(
        localRepositoryElement=local_element,
        craftRepositoryElement=craft_element,
        mirrorRepositoryElement=mirror_element,
    )

    settings_path.write_text(settings_xml)

    return settings_path


def update_pom(
    *, part_info: infos.PartInfo, add_distribution: bool, update_versions: bool
) -> None:
    pom_xml = part_info.part_build_subdir / "pom.xml"

    if not pom_xml.is_file():
        raise errors.PartsError("'pom.xml' does not exist")

    tree = ET.parse(pom_xml)

    project = tree.getroot()
    namespace = re.search("{(.*)}", project.tag).group(1)
    namespaces = {"": namespace}
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    if add_distribution:
        # Add a distributionManagement element, to tell "maven deploy" to deploy the
        # artifacts (jars and poms) to the export dir.
        distribution_dir = part_info.part_export_dir / "maven-use"
        distribution_element = ET.fromstring(
            DISTRIBUTION_REPO_TEMPLATE.format(repo_uri=distribution_dir.as_uri())
        )

        project.append(distribution_element)

    existing = _get_existing_artifacts(part_info)

    if update_versions:
        if dependencies := project.find("dependencies", namespaces):
            for dependency in dependencies.findall("dependency", namespaces):
                dep = _from_element(dependency, namespaces)
                versions = existing.get(dep.group_id, {}).get(dep.artifact_id, set())
                if versions:
                    _set_version(dependency, namespaces, next(iter(versions)))
                else:
                    print("problem")
        if (build := project.find("build", namespaces)) and (
            plugins := build.find("plugins", namespaces)
        ):
            for plugin in plugins.findall("plugin", namespaces):
                dep = _from_element(plugin, namespaces)
                versions = existing.get(dep.group_id, {}).get(dep.artifact_id, set())
                if versions:
                    _set_version(plugin, namespaces, next(iter(versions)))
                else:
                    print("problem")

    tree.write(pom_xml)


@dataclass
class MavenArtifact:
    group_id: str
    artifact_id: str
    version: str


ArtifactDict = dict[str, set[str]]
GroupDict = dict[str, ArtifactDict]


def _get_existing_artifacts(part_info: infos.PartInfo) -> GroupDict:
    result = GroupDict()

    search_locations = [
        part_info.backstage_dir / "maven-use",
        Path("/usr/share/maven-repo"),
    ]
    for loc in search_locations:
        if not loc.is_dir():
            continue
        for pom in loc.glob("**/*.pom"):
            art = _read_artifact(pom)
            group_artifacts = result.setdefault(art.group_id, {})
            versions = group_artifacts.setdefault(art.artifact_id, set())
            versions.add(art.version)

    return result


def _read_artifact(pom: Path) -> MavenArtifact:
    tree = ET.parse(pom)
    project = tree.getroot()
    namespaces = {}
    if match := re.search("{(.*)}", project.tag):
        namespace = match.group(1)
        namespaces = {"": namespace}
    return _from_element(project, namespaces)


def _from_element(element: ET.Element, namespaces: dict[str, str]) -> MavenArtifact:
    group_id = element.find("groupId", namespaces).text
    artifact_id = element.find("artifactId", namespaces).text
    version = element.find("version", namespaces).text

    return MavenArtifact(group_id, artifact_id, version)


def _set_version(
    element: ET.Element, namespaces: dict[str, str], new_version: str
) -> None:
    group_id = element.find("groupId", namespaces).text
    artifact_id = element.find("artifactId", namespaces).text

    version_element = element.find("version", namespaces)
    current_version = version_element.text
    version_element.text = new_version
    comment = ET.Comment(
        f"Version updated by craft-parts from '{current_version}' to '{new_version}'"
    )
    logger.debug(
        "Updating version of '%s.%s' from '%s' to '%s'",
        group_id,
        artifact_id,
        current_version,
        new_version,
    )
    element.append(comment)
