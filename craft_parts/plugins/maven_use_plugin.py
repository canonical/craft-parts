# Copyright 2020-2021,2024 Canonical Ltd.
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

"""The Maven Use plugin."""

import contextlib
from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import Literal
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET  # noqa: N817
from typing_extensions import override

from craft_parts import errors
from craft_parts.utils import process

from .base import Plugin
from .maven_plugin import MavenPluginEnvironmentValidator
from .properties import PluginProperties


@contextlib.context_manager
def ope(from_path: Path, to_path: Path) -> Iterator[Path]:
    """Temporarily replace a path with a symlink to another path.

    Context manager that replaces a specific path with a symlink to another path while it's active.
    :param from_path: The path to scooch out of the way for a moment
    :param to_path: The destination of the temporary link
    :yields: The temporary backup path (in case it's needed)
    """
    backup_path = from_path.with_stem(f"._tmp_{from_path.stem}")
    from_path.rename(backup_path)
    try:
        from_path.symlink_to(to_path)
        yield backup_path
    finally:
        backup_path.rename(from_path)


class MavenUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Maven Use plugin."""

    plugin: Literal["maven-use"] = "maven-use"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MavenUsePlugin(Plugin):
    """A plugin to setup the source into a Maven repository."""

    properties_class = MavenUsePluginProperties
    validator_class = MavenPluginEnvironmentValidator

    # TODO: try this???
    @classmethod
    @override
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set(
            "libmaven-compiler-plugin-java",
            "libmaven-resources-plugin-java",
            "libmaven-deploy-plugin-java",
            "libmaven-install-plugin-java",
            "libsurefire-java",
        )

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        commands = []
        maven_fetch_deps_cmd_template = (
            f"mvn dependency:get -DremoteRepositories=file://{self._part_info.backstage_dir}/maven-repo "
            "-DgroupId={groupId} -DartifactId={artifactId} -Dversion={version}"
        )

        # TODO: Use `mvn -s` instead of the weird temporary settings xml
        # Proxy both by extracting maven_plugin._create_settings
        # Don't worry about pre-existing user settings

        maven_settings_file = Path.home() / ".m2" / "settings.xml"
        settings_xml_tree = ET.parse(maven_settings_file)
        settings_xml = settings_xml_tree.getroot()

        # Add the Craft profile to Maven settings
        craft_profile = Element.parse(f"""\
            <profile>
                <id>craft</id>
                <repositories>
                    <repository>
                        <id>craft</id>
                        <name>craft packages</name>
                        <url>file://{self._part_info.backstage_dir}</url>
                    </repository>
                </repositories>
            </profile>
        """)
        if profiles := settings_xml.find("profiles"):
            profiles.append(craft_profile)
        else:
            profiles = Element("profiles")
            profiles.append(craft_profile)
            settings_xml.append(profiles)

        # Activate the Craft profile
        active_profile = Element.parse("<activeProfile>craft</activeProfile>")
        if active_profiles := settings_xml.find("activeProfiles"):
            active_profiles.append(active_profile)
        else:
            active_profiles = Element("activeProfiles")
            active_profiles.append(active_profile)
            settings_xml.append(active_profiles)

        # Add the Debian mirror to Maven settings
        debian_mirror = Element.parse("""\
            <mirror>
                <id>debian
                <mirrorOf>central</mirrorOf>
                <name>Mirror Repository from Debian Packages</name>
                <url>file:///usr/share/maven-repo</url>
            </mirror>
        """)
        if mirrors := settings_xml.find("mirrors"):
            mirrors.append(debian_mirror)
        else:
            mirrors = Element("mirrors")
            mirrors.append(debian_mirror)
            settings_xml.append(mirrors)

        # Add the "repository" to publish to - in this case, the part export directory


        with (
            NamedTemporaryFile(
                "w+", prefix="settings-", suffix=".xml"
            ) as temp_settings,
            ope(maven_settings_file, temp_settings),
        ):
            settings_xml_tree.write(temp_settings)

            self._part_info.part_export_dir

        # The download location for Maven dependencies cannot be specified - it will
        # always download to $HOME/.m2/repository. Thus, symlink to the local repository
        # # to force Maven to download there, then release the symlink
        # with ope(Path.home() / ".m2" / "repository", local_repo):
        #     for dependency in xml_root.iter("dependency"):
        #         dep_map = {}
        #         for field in ["groupId", "artifactId", "version"]:
        #             dep_map[field] = dependency.get("field")
        #             if not dep_map[field]:
        #                 raise errors.PluginBuildError(f"Invalid dependency in pom.xml: No {field} for dependency.")

        #         maven_fetch_deps_cmd = maven_fetch_deps_cmd_template.format_map(dep_map)
        #         commands.append(maven_fetch_deps_cmd)

        return commands
