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

"""The maven-use plugin."""

from __future__ import annotations

import os
import re
from typing import Literal, cast

from overrides import override

from craft_parts import errors

from . import validator
from ._maven_util import create_maven_settings, update_pom
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class MavenUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the maven plugin."""

    plugin: Literal["maven-use"] = "maven-use"

    maven_use_parameters: list[str] = []

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MavenUsePluginEnvironmentValidator(validator.PluginEnvironmentValidator):
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
        version = self.validate_dependency(
            dependency="mvn",
            plugin_name="maven",
            part_dependencies=part_dependencies,
        )
        if not re.match(r"(\x1b\[1m)?Apache Maven ", version) and (
            part_dependencies is None or "maven-use-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid maven version {version!r}",
            )


class MavenUsePlugin(JavaPlugin):
    """ """

    properties_class = MavenUsePluginProperties
    validator_class = MavenUsePluginEnvironmentValidator

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
        return "mvn"
        options = cast(MavenUsePluginProperties, self._options)
        return "${CRAFT_PART_BUILD_WORK}/mvnw" if options.maven_use_wrapper else "mvn"

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(MavenUsePluginProperties, self._options)

        mvn_cmd = [self._maven_executable, "deploy"]
        # if self._use_proxy():
        #     settings_path = self._part_info.part_build_dir / ".parts/.m2/settings.xml"
        #     _create_settings(settings_path)
        #     mvn_cmd += ["-s", str(settings_path)]
        # settings_path = self._part_info.part_build_subdir / ".parts/.m2/settings.xml"
        # local_repo = self._part_info.part_build_subdir / ".parts/.m2/repository"
        # craft_repo = self._part_info.backstage_dir
        settings_path = create_maven_settings(
            part_info=self._part_info, set_mirror=True
        )
        mvn_cmd += ["-s", str(settings_path)]

        update_pom(
            part_info=self._part_info, add_distribution=True, update_versions=True
        )

        return [
            # *self._get_mvnw_validation_commands(options=options),
            " ".join(mvn_cmd + options.maven_use_parameters),
            # *self._get_java_post_build_commands(),
        ]

    def _get_mvnw_validation_commands(
        self, options: MavenUsePluginProperties
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

    def _use_proxy(self) -> bool:
        env_vars_lower = list(map(str.lower, os.environ.keys()))
        return any(k in env_vars_lower for k in ("http_proxy", "https_proxy"))
