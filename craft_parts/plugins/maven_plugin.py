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

        :raises PluginEnvironmentValidationError: If go is invalid
          and there are no parts named go.
        """
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

        mvn_cmd = ["mvn", "package"]
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
