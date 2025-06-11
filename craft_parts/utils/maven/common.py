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
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from craft_parts import errors, infos

from ._xml import (
    CRAFT_REPO_TEMPLATE,
    DISTRIBUTION_REPO_TEMPLATE,
    LOCAL_REPO_TEMPLATE,
    MIRROR_REPO,
    PROXIES_TEMPLATE,
    PROXY_CREDENTIALS_TEMPLATE,
    PROXY_TEMPLATE,
    SETTINGS_TEMPLATE,
)

logger = logging.getLogger(__name__)


def create_maven_settings(
    *, part_info: infos.PartInfo, set_mirror: bool
) -> Path | None:
    """Create a Maven configuration file.

    The settings file contains additional configuration for Maven, such
    as proxy parameters.

    If it detects that no configuration is necessary, it will return None
    and do nothing.

    :param part_info: The part info for the part invoking Maven.

    :return: Returns a Path object to the settings file if one is created,
        otherwise None.
    """
    # Short-circuit exit if no config is needed
    if not (_needs_proxy_config() or set_mirror):
        return None

    settings_path = part_info.part_build_subdir / ".parts/.m2/settings.xml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    proxies_element = _get_proxy_config() if _needs_proxy_config() else ""

    if set_mirror:
        local_repo = part_info.part_build_subdir / ".parts/.m2/repository"
        backstage_repo = cast("Path", part_info.backstage_dir) / "maven-use"

        if backstage_repo.is_dir():
            # This is the shared repository in the backstage
            craft_element = CRAFT_REPO_TEMPLATE.format(repo_uri=backstage_repo.as_uri())
        else:
            craft_element = ""

        local_element = LOCAL_REPO_TEMPLATE.format(repo_dir=local_repo)
        mirror_element = MIRROR_REPO
    else:
        craft_element = local_element = mirror_element = ""

    settings_xml = SETTINGS_TEMPLATE.format(
        local_repository_element=local_element,
        craft_repository_element=craft_element,
        mirror_repository_element=mirror_element,
        proxies_element=proxies_element,
    )

    settings_path.write_text(settings_xml)

    return settings_path


def _get_proxy_config() -> str:
    """Generate an XML string for proxy configurations.

    Reads the environment for information on desired proxy settings and
    transforms those variables into Maven XML settings entries.
    """
    # Transform all environment variables to their lowercase form to support HTTPS_PROXY
    # vs. https_proxy and such
    case_insensitive_env = {item[0].lower(): item[1] for item in os.environ.items()}

    proxies: list[str] = []
    for protocol in ["http", "https"]:
        env_name = f"{protocol}_proxy"
        if env_name not in case_insensitive_env:
            continue

        proxy_url = urlparse(case_insensitive_env[env_name])
        if proxy_url.username is not None and proxy_url.password is not None:
            credentials = PROXY_CREDENTIALS_TEMPLATE.format(
                username=proxy_url.username, password=proxy_url.password
            )
        else:
            credentials = ""

        proxy_element = PROXY_TEMPLATE.format(
            id=env_name,
            protocol=protocol,
            host=proxy_url.hostname,
            port=proxy_url.port,
            credentials=credentials,
            non_proxy_hosts=_get_no_proxy_string(),
        )

        proxies.append(proxy_element)

    return PROXIES_TEMPLATE.format(proxies="\n".join(proxies))


def _needs_proxy_config() -> bool:
    """Determine whether or not proxy configuration is necessary for Maven."""
    proxy_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
    return any(key in os.environ for key in proxy_vars)


def _get_no_proxy_string() -> str:
    no_proxy = [k.strip() for k in os.environ.get("no_proxy", "localhost").split(",")]
    return "|".join(no_proxy)


def update_pom(
    *, part_info: infos.PartInfo, add_distribution: bool, update_versions: bool
) -> None:
    """Update the POM file of a Maven project.

    :param part_info: Information about the invoking part.
    :param add_distribution: Whether or not to configure the `mvn deploy` location.
    :param update_versions: Whether or not to patch version numbers with what is
        actually available.
    """
    pom_xml = part_info.part_build_subdir / "pom.xml"

    if not pom_xml.is_file():
        # TODO: this fails in tests; log instead?
        raise errors.PartsError("'pom.xml' does not exist")

    tree = ET.parse(pom_xml)  # noqa: S314, unsafe parsing with xml

    project = tree.getroot()
    namespace = re.search("{(.*)}", project.tag)
    if namespace is None:
        raise errors.PluginEnvironmentValidationError(
            part_name=part_info.part_name,
            reason="'pom.xml' could not be parsed: Unable to detect namespace.",
        )
    namespaces = {"": namespace.group(1)}
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    if add_distribution:
        # Add a distributionManagement element, to tell "maven deploy" to deploy the
        # artifacts (jars, poms, etc) to the export dir.
        distribution_dir = part_info.part_export_dir / "maven-use"
        distribution_element = ET.fromstring(  # noqa: S314, unsafe parsing with xml
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
                    raise MavenXMLError(
                        message=f"Dependency {dep.artifact_id} has no specified version."
                    )
        if (build := project.find("build", namespaces)) and (
            plugins := build.find("plugins", namespaces)
        ):
            for plugin in plugins.findall("plugin", namespaces):
                dep = _from_element(plugin, namespaces)
                versions = existing.get(dep.group_id, {}).get(dep.artifact_id, set())
                if versions:
                    _set_version(plugin, namespaces, next(iter(versions)))
                else:
                    raise MavenXMLError(
                        message=f"Dependency {dep.artifact_id} has no specified version."
                    )

    tree.write(pom_xml)


@dataclass
class MavenArtifact:
    """A dataclass for Maven artifacts."""

    group_id: str
    artifact_id: str
    version: str


ArtifactDict = dict[str, set[str]]
GroupDict = dict[str, ArtifactDict]


def _get_existing_artifacts(part_info: infos.PartInfo) -> GroupDict:
    result: GroupDict = GroupDict()

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
    tree = ET.parse(pom)  # noqa: S314, unsafe parsing with xml
    project = tree.getroot()
    namespaces = {}
    if match := re.search("{(.*)}", project.tag):
        namespace = match.group(1)
        namespaces = {"": namespace}
    return _from_element(project, namespaces)


def _from_element(element: ET.Element, namespaces: dict[str, str]) -> MavenArtifact:
    group_id = _get_element_text(_find_element(element, "groupId", namespaces))
    artifact_id = _get_element_text(_find_element(element, "artifactId", namespaces))
    version = _get_element_text(_find_element(element, "version", namespaces))

    return MavenArtifact(group_id, artifact_id, version)


def _set_version(
    element: ET.Element, namespaces: dict[str, str], new_version: str
) -> None:
    group_id = _get_element_text(_find_element(element, "groupId", namespaces))
    artifact_id = _get_element_text(_find_element(element, "artifactId", namespaces))

    version_element = _find_element(element, "version", namespaces)
    current_version = _get_element_text(version_element)

    if current_version == new_version:
        return

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


@dataclass
class MavenXMLError(BaseException):
    """An error encountered while parsing XML for Maven projects."""

    message: str


def _find_element(
    element: ET.Element, path: str, namespaces: dict[str, str]
) -> ET.Element:
    """Find a field within an element.

    This is equivalent to `element.find(path, namespaces)`, except that
    an exception is raised if the needle isn't found to reduce boilerplate.

    :param element: The haystack to search.
    :param path: The needle to find in the haystack.
    :param namespaces: A mapping of namespaces to use during the search.
    :raises _MavenXMLError: if the needle can't be found.
    :return: The discovered element.
    """
    if (needle := element.find(path, namespaces)) is not None:
        return needle

    raise MavenXMLError(message=f"Could not parse {path}.")


def _get_element_text(element: ET.Element) -> str:
    """Extract the text field from an element.

    This is equivalent to `element.text`, except that an exception is
    raised if the text field is empty to reduce boilerplate.

    :param element: The element to read from.
    :raises _MavenXMLError: if there is no text field.
    :return: The content of the text field.
    """
    if (text := element.text) is not None:
        return text

    raise MavenXMLError(message=f"No text field found on {element.tag}.")
