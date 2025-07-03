# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2025 Canonical Ltd.
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

import pathlib
import re
from typing import Literal, cast

from overrides import override

from craft_parts import errors
from craft_parts.utils.maven import create_maven_settings, update_pom

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class MavenPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the maven plugin."""

    plugin: Literal["maven"] = "maven"

    maven_parameters: list[str] = []
    maven_use_wrapper: bool = False

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
        if options.maven_use_wrapper:
            return
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
    - maven-use-wrapper:
      (boolean)
      Whether to use project's Maven wrapper (mvnw) to execute the build.
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

    @property
    def _maven_executable(self) -> str:
        """Return the maven executable to be used for build."""
        options = cast(MavenPluginProperties, self._options)
        return "${CRAFT_PART_BUILD_WORK}/mvnw" if options.maven_use_wrapper else "mvn"

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(MavenPluginProperties, self._options)

        mvn_cmd = [self._maven_executable, "package"]

        self_contained = self._is_self_contained()

        settings_path = create_maven_settings(
            part_info=self._part_info, set_mirror=self_contained
        )
        mvn_cmd.extend(["-s", str(settings_path)])

        if self_contained:
            update_pom(
                part_info=self._part_info,
                deploy_to=self._get_deploy_dir(),
                self_contained=True,
            )

        return [
            *self._get_mvnw_validation_commands(options=options),
            " ".join(mvn_cmd + options.maven_parameters),
            *self._get_extra_maven_commands(settings_path),
            *self._get_java_post_build_commands(),
        ]

    def _get_mvnw_validation_commands(
        self, options: MavenPluginProperties
    ) -> list[str]:
        """Validate mvnw file before execution."""
        if not options.maven_use_wrapper:
            return []
        return [
            """[ -e ${CRAFT_PART_BUILD_WORK}/mvnw ] || {
>&2 echo 'mvnw file not found, refer to plugin documentation: \
https://canonical-craft-parts.readthedocs-hosted.com/en/latest/\
common/craft-parts/reference/plugins/maven_plugin.html'; exit 1;
}"""
        ]

    def _get_deploy_dir(self) -> pathlib.Path | None:
        """Get the path that "mvn deploy" should write to.

        The default implementation returns None, which means that no deploying should
        happen.
        """
        return None

    def _get_extra_maven_commands(self, settings_path: pathlib.Path) -> list[str]:  # noqa: ARG002
        """Get the commands that should be executed after "mvn package".

        The default implementation is empty - this method is provided as a "hook" for
        subclasses.

        :param settings_path: The settings file that Maven commands should use.
        """
        return []

    @classmethod
    @override
    def supported_build_attributes(cls) -> set[str]:
        """Return the build attributes that this plugin supports."""
        return {"self-contained"}
