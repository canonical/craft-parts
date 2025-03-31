# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2023,2024,2025 Canonical Ltd.
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

"""The gradle plugin."""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from overrides import override
from pydantic import model_validator
from typing_extensions import Self

from craft_parts import errors

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties

_PLUGIN_PREFIX = "gradle-plugin"


class GradlePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the gradle plugin."""

    plugin: Literal["gradle"] = "gradle"

    gradle_init_script: str = ""
    gradle_init_script_parameters: list[str] = []
    gradle_parameters: list[str] = []
    gradle_task: str = "build"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    @model_validator(mode="after")
    def gradle_task_defined(self) -> Self:
        """Gradle task must be defined."""
        if not self.gradle_task:
            raise ValueError("Gradle task must be defined")
        return self


class GradlePluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the gradle plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @property
    def gradle_executable(self) -> str:
        """Use gradlew by default if it exists."""
        return "./gradlew" if Path("./gradlew").exists() else "gradle"

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If gradle is invalid
          and there are no parts named gradle-deps.
        """
        version = self.validate_dependency(
            dependency=self.gradle_executable,
            plugin_name="gradle",
            part_dependencies=part_dependencies,
            argument="--version 2>&1",
        )
        if not re.search(r"Gradle (.*)", version) and (
            part_dependencies is None or "gradle-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid gradle version {version!r}",
            )


class GradlePlugin(JavaPlugin):
    """A plugin to build parts that use Gradle.

    The Gradle build system is commonly used to build Java projects. This
    plugin requires a pom.xml in the root of the source tree.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

    - gradle-parameters:
      (list of strings)
      Flags to pass to the build using the gradle semantics for parameters.

    """

    properties_class = GradlePluginProperties
    validator_class = GradlePluginEnvironmentValidator

    @property
    def gradle_executable(self) -> str:
        """Use gradlew by default if it exists."""
        return (
            f"{self._part_info.part_build_dir}/gradlew"
            if (self._part_info.part_build_dir / "gradlew").exists()
            else "gradle"
        )

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
        options = cast(GradlePluginProperties, self._options)

        self._validate_project(options=options)
        gradle_cmd = [self.gradle_executable, options.gradle_task]
        self._setup_proxy()

        return [
            *self._get_gradle_init_command(options=options),
            " ".join(gradle_cmd + options.gradle_parameters),
            # remove gradle-wrapper.jar files
            *self._get_java_post_build_commands(),
        ]

    def _validate_project(self, options: GradlePluginProperties) -> None:
        if (
            options.gradle_init_script
            and not Path(
                self._part_info.part_build_dir / options.gradle_init_script
            ).exists()
        ):
            raise errors.FeatureError(
                message="gradle-init-script configured but not found in project",
                details=(
                    "See reference documentation for the plugin at "
                    "https://canonical-craft-parts.readthedocs-hosted.com"
                    "/en/latest/common/craft-parts/reference/plugins/gradle_plugin.html"
                ),
            )
        # Skip project version check if not using gradlew because the gradle provided by
        # apt is outdated and cannot run project version check init script.
        if self.gradle_executable == "gradle":
            return

        system_java_major_version = self.get_java_version()
        project_java_major_versions = self._get_project_java_major_version()
        if not all(
            system_java_major_version >= project_java_major_version
            for project_java_major_version in project_java_major_versions
        ):
            raise errors.PartSpecificationError(
                part_name=self._part_info.part_name,
                message="build Java version is less than project Java version.",
            )

    def _get_project_java_major_version(self) -> list[int]:
        """Return the project major version for all projects and subprojects."""
        init_script_path = Path(
            f"{self._part_info.part_build_dir}/{_PLUGIN_PREFIX}-init-script.gradle"
        )
        search_term = "gradle-plugin-java-version-print"
        init_script_path.write_text(
            f"""allprojects {{ project ->
    afterEvaluate {{
        if (project.hasProperty('java') && \
project.java.toolchain.languageVersion.getOrElse(false)) {{
            println "{search_term}: ${{project.java.toolchain.languageVersion.get().asInt()}}"
        }} else if (project.plugins.hasPlugin('java')) {{
            def javaVersion = project.targetCompatibility?: project.sourceCompatibility
            println "{search_term}: ${{javaVersion}}"
        }} else {{
            println "version not detected"
        }}
    }}
}}
""",
            encoding="utf-8",
        )
        try:
            version_output = subprocess.check_output(
                f"{self.gradle_executable} --init-script {init_script_path} 2>&1"
            )
        except subprocess.CalledProcessError as err:
            raise errors.PartSpecificationError(
                part_name=self._part_info.part_name,
                message="failed to execute project java version check",
            ) from err

        matches = re.findall(rf"{search_term}: (\d+)", version_output)
        if not matches:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_info.part_name,
                reason="project version not detected",
            )

        try:
            return [int(match) for match in matches]
        except ValueError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_info.part_name,
                reason=f"invalid java version detected: {err}",
            ) from err

    def _setup_proxy(self) -> None:
        no_proxy = os.environ.get("no_proxy", "")
        no_proxy = "|".join(no_proxy.split(",") if no_proxy else [])
        if not any(k in os.environ for k in ("http_proxy", "https_proxy")):
            return

        gradle_user_home = self._part_info.part_build_dir / ".gradle"
        gradle_user_home.mkdir(parents=True, exist_ok=True)
        gradle_properties = gradle_user_home / "gradle.properties"
        for protocol in ("http", "https"):
            env_name = f"{protocol}_proxy"
            if env_name not in os.environ:
                continue
            proxy_url = urlparse(os.environ[env_name])

            with open(
                gradle_properties, "a+", encoding="utf-8"
            ) as gradle_properties_file:
                gradle_properties_file.write(
                    f"""
systemProp.{protocol}.proxyHost={proxy_url.hostname}
systemProp.{protocol}.proxyPort={proxy_url.port}
systemProp.{protocol}.proxyUser={proxy_url.username}
systemProp.{protocol}.proxyPassword={proxy_url.password}
systemProp.{protocol}.nonProxyHosts={no_proxy}
"""
                )

    def _get_gradle_init_command(self, options: GradlePluginProperties) -> list[str]:
        if not options.gradle_init_script:
            return []
        gradle_cmd = [
            self.gradle_executable,
            "--init-script",
            options.gradle_init_script,
        ]
        return [" ".join(gradle_cmd + options.gradle_init_script_parameters)]
