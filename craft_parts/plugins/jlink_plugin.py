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

from typing import Any, Literal, cast

from pydantic import model_validator
from typing_extensions import Self, override

from .base import Plugin
from .properties import PluginProperties
from .validator import PluginEnvironmentValidator


class JLinkPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the JLink plugin."""

    plugin: Literal["jlink"] = "jlink"
    jlink_jars: list[str] = []
    jlink_extra_modules: list[str] = []
    jlink_modules: list[str] = []
    jlink_multi_release: int | str = "base"

    def _get_jlink_attributes(self, attribute_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            k: v
            for k, v in attribute_dict.items()
            if k.startswith("jlink") and k != "jlink_modules"
        }

    @model_validator(mode="after")
    def jlink_modules_exclusive(self) -> Self:
        """Option jlink_modules is exclusive with other options.

        This check ensures that the user does not set jlink_modules
        together with other options.
        """
        if self.jlink_modules:
            instance_dict = self._get_jlink_attributes(self.__dict__)
            class_dict = self._get_jlink_attributes(JLinkPluginProperties().__dict__)
            if class_dict != instance_dict:
                raise ValueError(
                    "Option jlink_modules is exclusive with all other options."
                )
        return self


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

    def _get_deps_commands(self) -> list[str]:
        """Return commands to generate a list of dependencies."""
        options = cast(JLinkPluginProperties, self._options)

        if options.jlink_modules:
            modules = ",".join(options.jlink_modules)
            return [f"deps={modules}"]

        return [
            self._get_multi_release_command(),
            self._get_find_jars_commands(),
            # create temp folder
            # extract jar files into temp folder - spring boot fat jar
            # contains dependent jars inside
            """
                mkdir -p "${CRAFT_PART_BUILD}/tmp" && \
                (cd "${CRAFT_PART_BUILD}/tmp" && \
                    for jar in ${PROCESS_JARS}; do jar xvf "${jar}"; done;)
            """,
            # create classpath - add all dependent jars and all staged jars
            "CPATH=.",
            # create classpath - add all dependent jars and all staged jars
            "CPATH=.",
            """\
                for file in $(find "${CRAFT_PART_BUILD}/tmp" -type f -name "*.jar"); do
                    CPATH="$CPATH:${file}"
                done
                for file in $(find "${CRAFT_STAGE}" -type f -name "*.jar"); do
                    CPATH="$CPATH:${file}"
                done
            """,
            """\
                if [ "x${PROCESS_JARS}" != "x" ]; then
                    deps=$(${JDEPS} --print-module-deps -q --recursive \
                        --ignore-missing-deps \
                        --multi-release ${MULTI_RELEASE} \
                        --class-path=${CPATH} \
                        ${PROCESS_JARS})
                else
                    deps=java.base
                fi
            """,
        ]

    def _get_multi_release_command(self) -> str:
        """Return jdeps multi-release setting."""
        options = cast(JLinkPluginProperties, self._options)
        return f"MULTI_RELEASE={options.jlink_multi_release}"

    def _get_extra_module_list(self) -> str:
        """Return additional modules."""
        options = cast(JLinkPluginProperties, self._options)
        return ",".join([x.strip() for x in options.jlink_extra_modules])

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
        commands = [
            # Set JAVA_HOME to be used in jlink commands
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
            """,
            # extract jlink version and use it to define the destination
            # and multi-release jar version for the dependency enumeration
            "JLINK_VERSION=$(${JLINK} --version)",
            "DEST=usr/lib/jvm/java-${JLINK_VERSION%%.*}-openjdk-${CRAFT_ARCH_BUILD_FOR}",
            "INSTALL_ROOT=${CRAFT_PART_INSTALL}/${DEST}",
            *self._get_deps_commands(),
        ]
        extra_modules = self._get_extra_module_list()
        if len(extra_modules) > 0:
            commands.append(f"deps=${{deps}},{extra_modules}")

        commands.append(
            "rm -rf ${INSTALL_ROOT} && ${JLINK} --no-header-files --no-man-pages --strip-debug --add-modules ${deps} --output ${INSTALL_ROOT}"
        )
        # create /usr/bin/java link
        commands.append(
            "(cd ${CRAFT_PART_INSTALL} && mkdir -p usr/bin && ln -s --relative ${DEST}/bin/java usr/bin/)"
        )
        return commands
