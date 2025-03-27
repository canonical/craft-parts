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

        options = cast(GradlePluginProperties, self._options)
        if options.gradle_init_script and not Path(options.gradle_init_script).exists():
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason="gradle init script option supplied but file not found",
            )

        # Skip project version check if not using gradlew because the gradle provided by
        # apt is outdated and cannot run project version check init script.
        if self.gradle_executable == "gradle":
            return

        system_java_major_version = self._get_system_java_major_version()
        project_java_major_version = self._get_project_java_major_version()
        if system_java_major_version < project_java_major_version:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason="system Java version is less than project Java version"
                f"system: {system_java_major_version}, project: {project_java_major_version}",
            )

    def _get_system_java_major_version(self) -> int:
        try:
            system_java_version_output = self._execute("java --version")
            # Java versions < 8 have syntax 1.<version>
        except subprocess.CalledProcessError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to check java version: {err}",
            ) from err
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
        try:
            return int(system_java_major_version)
        except ValueError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to parse java version: {err}",
            ) from err

    def _get_project_java_major_version(self) -> int:
        init_script_path = Path(f"/tmp/{_PLUGIN_PREFIX}-init-script.gradle")
        task_name = f"{_PLUGIN_PREFIX}-printProjectJavaVersion"
        init_script_path.write_text(
            f"""allprojects {{
    tasks.register('{task_name}') {{
        doLast {{
            def systemJavaVersion = JavaLanguageVersion.current()
            def javaVersion = java.toolchain.languageVersion.\
orElse(systemJavaVersion).get().asInt()
            println "Project Java Version: ${{javaVersion}}"
        }}
    }}
}}
""",
            encoding="utf-8",
        )
        try:
            version_output = self._execute(
                f"{self.gradle_executable} --init-script {init_script_path} {task_name} 2>&1"
            )
        except subprocess.CalledProcessError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason="failed to execute project java version check",
            ) from err

        version_output_match = re.search(r"Project Java Version: (\d+)", version_output)
        if not version_output_match:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to parse project java version: {version_output}",
            )
        try:
            return int(version_output_match.group(1))
        except ValueError as err:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"failed to parse project java version: {err}",
            ) from err


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
        return "./gradlew" if Path("./gradlew").exists() else "gradle"

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

        gradle_cmd = [self.gradle_executable, options.gradle_task]
        self._setup_proxy()

        return [
            *self._get_gradle_init_command(),
            " ".join(gradle_cmd + options.gradle_parameters),
            *self._get_java_post_build_commands(),
        ]

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

    def _get_gradle_init_command(self) -> list[str]:
        options = cast(GradlePluginProperties, self._options)
        if not options.gradle_init_script:
            return []
        gradle_cmd = [
            self.gradle_executable,
            "--init-script",
            options.gradle_init_script,
        ]
        return [" ".join(gradle_cmd + options.gradle_init_script_parameters)]
