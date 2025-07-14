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

import re
from typing import Literal, cast

from overrides import override

from craft_parts import errors
from craft_parts.utils.maven import create_maven_settings, update_pom
from craft_parts.utils.maven.common import MavenXMLError

from . import validator
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
            part_dependencies is None or "maven-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid maven version {version!r}",
            )


class MavenUsePlugin(JavaPlugin):
    """The Maven use plugin."""

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
        mvnw = self._part_info.part_build_subdir / "mvnw"
        return str(mvnw) if mvnw.is_file() else "mvn"

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        if self._use_binaries():
            return self._get_binaries_commands()

        options = cast(MavenUsePluginProperties, self._options)

        mvn_cmd = [self._maven_executable, "deploy"]

        self_contained = self._is_self_contained()

        settings_path = create_maven_settings(
            part_info=self._part_info, set_mirror=self_contained
        )
        mvn_cmd += ["-s", str(settings_path)]

        try:
            update_pom(
                part_info=self._part_info,
                deploy_to=self._part_info.part_export_dir,
                self_contained=self_contained,
            )
        except MavenXMLError as err:
            raise errors.PartsError(
                brief=f"Plugin configuration failed for part {self._part_info.part_name}: {err.message}",
                details=err.details,
                resolution="Check that the 'pom.xml' file is valid.",
            )

        return [
            " ".join(mvn_cmd + options.maven_use_parameters),
        ]

    @classmethod
    @override
    def supported_build_attributes(cls) -> set[str]:
        """Return the build attributes that this plugin supports."""
        return {"self-contained"}

    def _use_binaries(self) -> bool:
        """Whether the build should consume binaries directly, or build from source."""
        maven_use = self._part_info.part_build_subdir / "maven-use"
        return maven_use.is_dir()

    def _get_binaries_commands(self) -> list[str]:
        """Get the commands needed to "build" the source from pre-built binaries."""
        maven_use = self._part_info.part_build_subdir / "maven-use"

        self_contained = self._is_self_contained()
        try:
            for pom_file in maven_use.glob("**/*.pom"):
                update_pom(
                    part_info=self._part_info,
                    deploy_to=None,
                    self_contained=self_contained,
                    pom_file=pom_file,
                )
        except MavenXMLError as err:
            raise errors.PartsError(
                brief=f"Plugin configuration failed for part {self._part_info.part_name}: {err.message}",
                details=err.details,
            )

        export_dir = self._part_info.part_export_dir
        return [f'cp --archive --link --no-dereference ./maven-use "{export_dir}"']
