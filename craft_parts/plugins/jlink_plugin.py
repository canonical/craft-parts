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


class JLinkPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the JLink plugin."""

    plugin: Literal["jlink"] = "jlink"
    jlink_java_version: int = 21
    jlink_jars: list[str] = []


class JLinkPlugin(Plugin):
    """Create a Java Runtime using JLink."""

    properties_class = JLinkPluginProperties

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        options = cast(JLinkPluginProperties, self._options)
        return {f"openjdk-{options.jlink_java_version}-jdk"}

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
        options = cast(JLinkPluginProperties, self._options)

        commands = []

        java_home = f"usr/lib/jvm/java-{options.jlink_java_version}-openjdk-${{CRAFT_TARGET_ARCH}}"

        if len(options.jlink_jars) > 0:
            jars = " ".join(["${CRAFT_STAGE}/" + x for x in options.jlink_jars])
            commands.append(f"PROCESS_JARS={jars}")
        else:
            commands.append("PROCESS_JARS=$(find ${CRAFT_STAGE} -type f -name *.jar)")

        # create temp folder
        commands.append("mkdir -p ${CRAFT_PART_BUILD}/tmp")
        # extract jar files into temp folder
        commands.append(
            "(cd ${CRAFT_PART_BUILD}/tmp && for jar in ${PROCESS_JARS}; do jar xvf ${jar}; done;)"
        )
        commands.append("CPATH=$(find ${CRAFT_PART_BUILD}/tmp -type f -name *.jar)")
        commands.append("CPATH=$(CPATH):$(find ${CRAFT_STAGE} -type f -name *.jar)")
        commands.append("CPATH=$(echo ${CPATH}:. | sed s'/[[:space:]]/:/'g)")
        commands.append("echo ${CPATH}")
        commands.append(
            f"""if [ "x${{PROCESS_JARS}}" != "x" ]; then
                deps=$(jdeps --class-path=${{CPATH}} -q --recursive  --ignore-missing-deps \
                    --print-module-deps --multi-release {options.jlink_java_version} ${{PROCESS_JARS}})
                else
                    deps=java.base
                fi
            """
        )
        commands.append(f"INSTALL_ROOT=${{CRAFT_PART_INSTALL}}/{java_home}")

        commands.append(
            "rm -rf ${INSTALL_ROOT} && jlink --add-modules ${deps} --output ${INSTALL_ROOT}"
        )
        # create /usr/bin/java link
        commands.append(
            f"(cd ${{CRAFT_PART_INSTALL}} && mkdir -p usr/bin && ln -s --relative {java_home}/bin/java usr/bin/)"
        )
        return commands
