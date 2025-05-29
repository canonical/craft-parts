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

"""The Maven Use plugin."""

from pathlib import Path
from textwrap import dedent
from typing import Literal, cast
from xml.etree import ElementTree as ET

from typing_extensions import override

from craft_parts.utils import maven_utils

from .base import Plugin
from .maven_plugin import MavenPluginEnvironmentValidator
from .properties import PluginProperties


class MavenUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Maven Use plugin."""

    plugin: Literal["maven-use"] = "maven-use"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MavenUsePlugin(Plugin):
    """A plugin to setup the source into a Maven repository."""

    properties_class = MavenUsePluginProperties
    validator_class = MavenPluginEnvironmentValidator

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
        return {
            "libmaven-compiler-plugin-java",
            "libmaven-resources-plugin-java",
            "libmaven-deploy-plugin-java",
            "libmaven-install-plugin-java",
            "libsurefire-java",
        }

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        # TODO: Proxy both by extracting maven_plugin._create_settings

        # Create temporary Maven settings. Each of these settings does the following:
        # <localRepository> configures where Maven will publish built artifacts
        # <mirrors> allows us to override the "central" repository, Maven's equivalent to Python's PyPI.
        #   This allows us to give Maven a place to look for packages it needs that can be acquired as debs
        # <profiles> is where we configure a directory for Maven to look for dependencies, Maven's equivalent
        #   to a local Python index
        # <activeProfiles> simply activates the profile specified above
        settings_file = cast("Path", self._part_info.work_dir) / "settings.xml"

        local_repository = ET.Element("localRepository")
        local_repository.text = str(self._part_info.part_export_dir)

        debian_mirror = ET.Element("mirror")
        debian_mirror_tags = [
            ("id", "debian"),
            ("mirrorOf", "central"),
            ("name", "Mirror Repository from Debian Packages"),
            ("url", "file:///usr/share/maven-repo"),
        ]
        maven_utils.add_xml_tags(debian_mirror, debian_mirror_tags)
        mirrors = ET.Element("mirrors")
        mirrors.append(debian_mirror)

        craft_repository = ET.Element("repository")
        craft_repository_tags = [
            ("id", "craft"),
            ("name", "craft packages"),
            ("url", f"file://{self._part_info.backstage_dir}"),
        ]
        maven_utils.add_xml_tags(craft_repository, craft_repository_tags)
        repositories = ET.Element("repositories")
        repositories.append(craft_repository)

        profile_id = ET.Element("id")
        profile_id.text = "craft"
        profile = ET.Element("profile")
        profile.append(profile_id)
        profile.append(repositories)

        profiles = ET.Element("profiles")
        profiles.append(profile)

        active_profile = ET.Element("activeProfile")
        active_profile.text = "craft"
        active_profiles = ET.Element("activeProfiles")
        active_profiles.append(active_profile)

        maven_utils.create_settings(
            settings_file,
            extra_elements=[local_repository, mirrors, profiles, active_profiles],
        )

        return [
            f"maven -U -s {settings_file} -f {self._part_info.part_build_subdir} install"
        ]
