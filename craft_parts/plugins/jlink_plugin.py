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

"""The JLink plugin."""

from typing import Literal, cast

from overrides import override

from .base import Plugin
from .properties import PluginProperties
from .validator import PluginEnvironmentValidator


class JLinkPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the JLink plugin."""

    plugin: Literal["jlink"] = "jlink"
    jlink_jars: list[str] = []


class JLinkPluginEnvironmentValidator(PluginEnvironmentValidator):
    """Check the execution environment for the JLink plugin.

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
            dependency="jlink", plugin_name="jlink", part_dependencies=part_dependencies
        )


class JLinkPlugin(Plugin):
    """Create a Java Runtime using JLink."""

    properties_class = JLinkPluginProperties
    validator_class = JLinkPluginEnvironmentValidator

    def _get_find_jars_commands(self) -> str:
        """Return commands for finding all jarfiles."""
        options = cast(JLinkPluginProperties, self._options)
        if len(options.jlink_jars) > 0:
            jars = " ".join(["${CRAFT_STAGE}/" + x for x in options.jlink_jars])
            return f"PROCESS_JARS={jars}"

        return 'PROCESS_JARS=$(find ${CRAFT_STAGE} -type f -name "*.jar")'

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

        # Set JAVA_HOME to be used in jlink commands
        commands.append(
            """
                if [ -z "${JAVA_HOME+x}" ]; then
                    JAVA_HOME=$(dirname $(dirname $(readlink -f $(which jlink))))
                fi
                if [ ! -x "${JAVA_HOME}/bin/java" ]; then
                    echo "Error: JAVA_HOME: '${JAVA_HOME}/bin/java' is not an executable." >&2
                    exit 1
                fi
                JLINK=${JAVA_HOME}/bin/jlink
                JDEPS=${JAVA_HOME}/bin/jdeps
            """
        )

        # extract jlink version and use it to define the destination
        # and multi-release jar version for the dependency enumeration
        commands.append("JLINK_VERSION=$(${JLINK} --version)")
        commands.append(
            "DEST=usr/lib/jvm/java-${JLINK_VERSION%%.*}-openjdk-${CRAFT_ARCH_BUILD_FOR}"
        )
        commands.append("MULTI_RELEASE=${JLINK_VERSION%%.*}")

        commands.append(self._get_find_jars_commands())

        # create temp folder
        commands.append("mkdir -p ${CRAFT_PART_BUILD}/tmp")
        # extract jar files into temp folder - spring boot fat jar
        # contains dependent jars inside
        commands.append(
            "(cd ${CRAFT_PART_BUILD}/tmp && for jar in ${PROCESS_JARS}; do jar xvf ${jar}; done;)"
        )
        # create classpath - add all dependent jars and all staged jars
        commands.append("CPATH=.")
        commands.append(
            """
                for file in $(find "${CRAFT_PART_BUILD}/tmp" -type f -name "*.jar"); do
                    CPATH="$CPATH:${file}"
                done
                for file in $(find "${CRAFT_STAGE}" -type f -name "*.jar"); do
                    CPATH="$CPATH:${file}"
                done
            """
        )
        commands.append(
            """if [ "x${PROCESS_JARS}" != "x" ]; then
                deps=$(${JDEPS} --print-module-deps -q --recursive \
                    --ignore-missing-deps \
                    --multi-release ${MULTI_RELEASE} \
                    --class-path=${CPATH} \
                    ${PROCESS_JARS})
                else
                    deps=java.base
                fi
            """
        )
        commands.append("INSTALL_ROOT=${CRAFT_PART_INSTALL}/${DEST}")

        commands.append(
            "rm -rf ${INSTALL_ROOT} && ${JLINK} --no-header-files --no-man-pages --strip-debug --add-modules ${deps} --output ${INSTALL_ROOT}"
        )
        # create /usr/bin/java link
        commands.append(
            "(cd ${CRAFT_PART_INSTALL} && mkdir -p usr/bin && ln -s --relative ${DEST}/bin/java usr/bin/)"
        )
        return commands
