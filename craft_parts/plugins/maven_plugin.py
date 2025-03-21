# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2023,2024 Canonical Ltd.
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

"""The maven plugin."""

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from overrides import override

from craft_parts import errors

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class MavenPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the maven plugin."""

    plugin: Literal["maven"] = "maven"

    maven_parameters: list[str] = []
    maven_use_mvnw: bool = False
    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MavenPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the maven plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If maven is invalid
          and there are no parts named maven-deps.
        """
        options = cast(MavenPluginProperties, self._options)
        if options.maven_use_mvnw:
            version = self.validate_dependency(
                dependency="./mvnw",
                plugin_name="maven",
                part_dependencies=part_dependencies,
            )
        else:
            version = self.validate_dependency(
                dependency="mvn",
                plugin_name="maven",
                part_dependencies=part_dependencies,
            )
        if not re.match(r"(\x1b\[1m)?Apache Maven ", version) and (
            part_dependencies is None or "maven-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid maven version {version!r}",
            )

        try:
            system_java_version_output = self._execute("java --version")
            # Java versions < 8 have syntax 1.<version>
            version_output_match = re.match(
                r"openjdk (1\.(\d+)|(\d+))", system_java_version_output
            )
            if version_output_match is None:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"failed to check java version: {system_java_version_output}",
                )
            # match 1.<version> first for Java versions less than or equal to 8. Otherwise,
            # match <version>.
            system_java_major_version = version_output_match.group(
                2
            ) or version_output_match.group(1)
        except subprocess.CalledProcessError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to check java version: {err}",
            ) from err

        maven_executable = "./mvnw" if options.maven_use_mvnw else "mvn"
        effective_pom_path = Path("effective.pom")
        try:
            self._execute(
                # Write to file since writing to stdout without maven info logs require sudo, i.e.
                # sudo mvn help:effective-pom -q -DforceStdout -doutput=/dev/stdout
                f"{maven_executable} help:effective-pom -Doutput={effective_pom_path}"
            )
            project_java_major_version = _parse_project_java_version(effective_pom_path)
            project_java_major_version = _extract_java_version(
                project_java_major_version
            )
            # if the project Java version cannot be detected, let it try build anyway.
            if project_java_major_version is None:
                return
        except subprocess.CalledProcessError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to generate effective pom: {err}",
            ) from err
        finally:
            effective_pom_path.unlink(missing_ok=True)

        try:
            if int(system_java_major_version) < int(project_java_major_version):
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="system Java version is less than project Java version."
                    f"system: {system_java_major_version}, project: {project_java_major_version}",
                )
        except ValueError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to compare java versions: {err}, "
                f"system: {system_java_major_version}, project: {project_java_major_version}",
            ) from err


def _parse_project_java_version(effective_pom_path: Path) -> str | None:
    """Parse the contents of effective pom XML file.

    The order in which Maven determines the Java version is as follows:
    1. maven-compiler-plugin's configuration release value
    2. maven-compiler-plugin's property's release value
    3. java.version property's value (Spring Boot specific)
    """
    tree = ET.parse(effective_pom_path)
    root = tree.getroot()
    java_version_element = root.find(".//{*}java.version")
    maven_compiler_release_element = root.find(".//{*}maven.compiler.release")
    maven_compiler_plugin_release_element = None
    plugins_element = root.find(".//{*}plugins")
    if plugins_element is not None:
        plugins = plugins_element.findall(".//{*}plugin")
        for plugin in plugins:
            if (
                artifact_id_element := plugin.find(".//{*}artifactId")
            ) is not None and artifact_id_element.text == "maven-compiler-plugin" and (
                release_element := plugin.find(".//{*}release")) is not None and release_element.text:
                maven_compiler_plugin_release_element = release_element
                break
    if (
        maven_compiler_plugin_release_element is not None
        and maven_compiler_plugin_release_element.text
    ):
        return maven_compiler_plugin_release_element.text
    if (
        maven_compiler_release_element is not None
        and maven_compiler_release_element.text
    ):
        return maven_compiler_release_element.text
    if java_version_element is not None and java_version_element.text:
        return java_version_element.text
    return None


def _extract_java_version(java_version_output: str | None) -> str | None:
    if java_version_output is None:
        return None
    match = re.match(r"(1\.(\d+)|(\d+))", java_version_output)
    if not match:
        return None
    return match.group(2) or match.group(1)


class MavenPlugin(JavaPlugin):
    """A plugin to build parts that use Maven.

    The Maven build system is commonly used to build Java projects. This
    plugin requires a pom.xml in the root of the source tree.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

    - maven-parameters:
      (list of strings)
      Flags to pass to the build using the maven semantics for parameters.
    - maven-use-mvnw:
      (boolean)
      Use the Maven wrapper script (mvnw) instead of the system Maven
      installation.
    """

    properties_class = MavenPluginProperties
    validator_class = MavenPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(MavenPluginProperties, self._options)

        mvn_executable = "./mvnw" if options.maven_use_mvnw else "mvn"
        mvn_cmd = [mvn_executable, "package"]
        if self._use_proxy():
            settings_path = self._part_info.part_build_dir / ".parts/.m2/settings.xml"
            _create_settings(settings_path)
            mvn_cmd += ["-s", str(settings_path)]

        return [
            " ".join(mvn_cmd + options.maven_parameters),
            *self._get_java_post_build_commands(),
        ]

    def _use_proxy(self) -> bool:
        return any(k in os.environ for k in ("http_proxy", "https_proxy"))


def _create_settings(settings_path: Path) -> None:
    """Create a Maven configuration file.

    The settings file contains additional configuration for Maven, such
    as proxy parameters.

    :param settings_path: the location the settings file will be created.
    """
    settings = ET.Element(
        "settings",
        attrib={
            "xmlns": "http://maven.apache.org/SETTINGS/1.0.0",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": (
                "http://maven.apache.org/SETTINGS/1.0.0 "
                "http://maven.apache.org/xsd/settings-1.0.0.xsd"
            ),
        },
    )
    element = ET.Element("interactiveMode")
    element.text = "false"
    settings.append(element)
    proxies = ET.Element("proxies")

    for protocol in ("http", "https"):
        env_name = f"{protocol}_proxy"
        if env_name not in os.environ:
            continue

        proxy_url = urlparse(os.environ[env_name])
        proxy = ET.Element("proxy")
        proxy_tags = [
            ("id", env_name),
            ("active", "true"),
            ("protocol", protocol),
            ("host", proxy_url.hostname),
            ("port", str(proxy_url.port)),
        ]
        if proxy_url.username is not None:
            proxy_tags.extend(
                [("username", proxy_url.username), ("password", proxy_url.password)]
            )
        proxy_tags.append(("nonProxyHosts", _get_no_proxy_string()))

        for tag, text in proxy_tags:
            element = ET.Element(tag)
            element.text = text
            proxy.append(element)

        proxies.append(proxy)

    settings.append(proxies)
    tree = ET.ElementTree(settings)
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)

    with settings_path.open("w") as file:
        tree.write(file, encoding="unicode")
        file.write("\n")


def _get_no_proxy_string() -> str:
    no_proxy = [k.strip() for k in os.environ.get("no_proxy", "localhost").split(",")]
    return "|".join(no_proxy)
