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
from textwrap import dedent
from typing import Literal, cast
from urllib.parse import urlparse

from overrides import override
from pydantic import model_validator
from typing_extensions import Self

from . import validator
from .java_plugin import JavaPlugin
from .properties import PluginProperties


class GradlePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the gradle plugin.

    - gradle_init_script:
      (string)
      The path to init script to run before build script is executed.
    - gradle_parameters:
      (list of strings)
      Extra arguments to pass along to Gradle task execution.
    - gradle_task:
      (string)
      The task to run to build the project.
    """

    plugin: Literal["gradle"] = "gradle"

    gradle_init_script: str = ""
    gradle_parameters: list[str] = []
    gradle_task: str = "build"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    @model_validator(mode="after")
    def gradle_task_defined(self) -> Self:
        """Gradle task must be defined.

        This check ensures that the user does not override the default value "build" with an
        empty string.
        """
        if not self.gradle_task:
            raise ValueError("gradle-task must be defined")
        return self


class GradlePluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the gradle plugin.

    We can't check for gradle executable here because if the project uses gradlew, we don't
    necessarily need gradle to be installed on the system. We can't check if the project uses
    gradlew since the project would not be pulled yet.
    """


class GradlePlugin(JavaPlugin):
    """A plugin to build parts that use Gradle.

    The Gradle build system is commonly used to build Java projects. This
    plugin requires a build.gradle in the root of the source tree.
    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

    - gradle-init-script:
      (list of strings)
      Path to the Gradle init script to use during build task execution.
    - gradle-parameters:
      (list of strings)
      Flags to pass to the build using the gradle semantics for parameters.
    - gradle_task:
      (string)
      The task to run to build the project.
    """

    properties_class = GradlePluginProperties
    validator_class = GradlePluginEnvironmentValidator

    @property
    def gradle_executable(self) -> str:
        """Use gradlew by default if it exists."""
        return (
            f"{self._part_info.part_build_subdir}/gradlew"
            if (self._part_info.part_build_subdir / "gradlew").exists()
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

        gradle_cmd = [self.gradle_executable, options.gradle_task]
        self._setup_proxy()

        return [
            " ".join(
                gradle_cmd
                + self._get_gradle_init_command_args(options=options)
                + options.gradle_parameters
            ),
            # remove gradle-wrapper.jar files included in the project if any.
            f'find {self._part_info.part_build_subdir} -name "gradle-wrapper.jar" -type f -delete',
            *self._get_java_post_build_commands(),
        ]

    def _setup_proxy(self) -> None:
        case_insensitive_env = {item[0].lower(): item[1] for item in os.environ.items()}
        no_proxy = case_insensitive_env.get("no_proxy", "")
        no_proxy = "|".join(no_proxy.split(",") if no_proxy else [])
        if not any(k in case_insensitive_env for k in ("http_proxy", "https_proxy")):
            return

        gradle_user_home = self._part_info.part_build_subdir / ".gradle"
        gradle_user_home.mkdir(parents=True, exist_ok=True)
        gradle_properties = gradle_user_home / "gradle.properties"
        for protocol in ("http", "https"):
            env_name = f"{protocol}_proxy"
            if env_name not in case_insensitive_env:
                continue
            proxy_url = urlparse(case_insensitive_env[env_name])

            with open(
                gradle_properties, "a+", encoding="utf-8"
            ) as gradle_properties_file:
                gradle_properties_file.write(
                    dedent(
                        f"""\
                        systemProp.{protocol}.proxyHost={proxy_url.hostname}
                        systemProp.{protocol}.proxyPort={proxy_url.port}
                        systemProp.{protocol}.proxyUser={proxy_url.username}
                        systemProp.{protocol}.proxyPassword={proxy_url.password}
                        systemProp.{protocol}.nonProxyHosts={no_proxy}
                        """
                    )
                )

    def _get_gradle_init_command_args(
        self, options: GradlePluginProperties
    ) -> list[str]:
        if not options.gradle_init_script:
            return []
        return [
            "--init-script",
            options.gradle_init_script,
        ]
