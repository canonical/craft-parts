# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

"""The Spring Boot plugin."""

import textwrap
from typing import Literal

from overrides import override

from .base import Plugin
from .properties import PluginProperties
from .validator import PluginEnvironmentValidator


class SpringBootPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Spring Boot plugin."""

    plugin: Literal["spring-boot"] = "spring-boot"


class SpringBootPluginEnvironmentValidator(PluginEnvironmentValidator):
    """Check the execution environment for the Spring Boot plugin.

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
        self.validate_dependency(
            dependency="java",
            plugin_name="spring-boot",
            part_dependencies=part_dependencies,
        )


class SpringBootPlugin(Plugin):
    """Build the Spring Boot application."""

    properties_class = SpringBootPluginProperties
    validator_class = SpringBootPluginEnvironmentValidator

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        commands = []
        # Set JAVA_HOME
        commands.append(
            textwrap.dedent(
                """\
                if [ -z "${JAVA_HOME+x}" ]; then
                    JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
                fi
                """
            )
        )
        # Set project base
        commands.append(
            textwrap.dedent(
                """\
                if [[ -e "./mvnw" ]]; then
                    PROJECT_BASE="maven"
                elif [[ -e "./gradlew" ]]; then
                    PROJECT_BASE="gradle"
                else
                    echo 'Neither "mvnw" nor "gradlew" found.'
                    exit 1
                fi
                """
            )
        )
        # Check executability of wrapper files
        commands.append(
            textwrap.dedent(
                """\
                if [[ "$PROJECT_BASE" == "maven" && ! -x "./mvnw" ]]; then
                    echo '"mvnw" found but not executable.'
                    exit 1
                elif [[ "$PROJECT_BASE" == "gradle" && ! -x "./gradlew" ]]; then
                    echo '"gradlew" found but not executable.'
                    exit 1
                fi
                """
            )
        )

        # Check system Java version compatibility with project Java version
        commands.append(
            textwrap.dedent(
                """\
                SYSTEM_JAVA_MAJOR_VERSION=$($JAVA_HOME/bin/java -version 2>&1 | grep -oP \
                'openjdk version "\\K(1\\.\\d+|\\d+)')
                """
            )
        )
        commands.append(
            textwrap.dedent(
                """\
                if [[ "$PROJECT_BASE" == "maven" ]]; then
                    PROJECT_JAVA_VERSION=$("./mvnw" help:evaluate -Dexpression=project.properties \
                -q -DforceStdout | grep -oP '<java\\.version>\\K(.*?)(?=</java\\.version>)')
                elif [[ "$PROJECT_BASE" == "gradle" ]]; then
                    PROJECT_JAVA_VERSION=$("./gradlew" javaToolchains | grep -oP \
                    "Language Version:\\s+\\K(\\d+)")
                fi
                """
            )
        )
        commands.append(
            textwrap.dedent(
                """\
                if [[ $PROJECT_JAVA_VERSION -gt $SYSTEM_JAVA_MAJOR_VERSION ]]; then
                    echo "Project requires Java version $PROJECT_JAVA_VERSION, but system Java \
                version is $SYSTEM_JAVA_MAJOR_VERSION."
                    exit 1
                fi
                """
            )
        )

        # Run build
        commands.append(
            textwrap.dedent(
                """\
                if [[ "$PROJECT_BASE" == "maven" ]]; then
                    ./mvnw clean install
                elif [[ "$PROJECT_BASE" == "gradle" ]]; then
                    ./gradlew build
                fi
                """
            )
        )

        # Install build
        commands.append(
            textwrap.dedent(
                """\
                if [[ "$PROJECT_BASE" == "maven" ]]; then
                    cp ${CRAFT_PART_BUILD}/target/*.jar ${CRAFT_PART_INSTALL}/
                elif [[ "$PROJECT_BASE" == "gradle" ]]; then
                    rm ${CRAFT_PART_BUILD}/build/libs/*plain*.jar
                    cp ${CRAFT_PART_BUILD}/build/libs/*.jar ${CRAFT_PART_INSTALL}/
                fi
                """
            )
        )

        # Install tmp dir (unavailble in bare base)
        commands.append(
            textwrap.dedent(
                """\
                mkdir -p ${CRAFT_PRIME}/tmp
                chown 584792 ${CRAFT_PRIME}/tmp
                """
            )
        )

        return commands
