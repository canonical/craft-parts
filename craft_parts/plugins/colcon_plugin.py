# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*
#
# Copyright 2026 Canonical Ltd.
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

"""The colcon plugin implementation."""

import pathlib
from typing import Literal, cast

from typing_extensions import override

from .base import Plugin
from .properties import PluginProperties


class ColconPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the colcon plugin."""

    plugin: Literal["colcon"] = "colcon"

    colcon_cmake_args: list[str] = []
    colcon_packages: list[str] = []
    colcon_packages_ignore: list[str] = []

    # part properties required by the plugin
    source: str  # type: ignore[reportGeneralTypeIssues]


class ColconPlugin(Plugin):
    """A plugin useful for building colcon-based parts."""

    properties_class = ColconPluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {
            "gcc",
            "g++",
            "cmake",
            "python3-colcon-core",
            "python3-colcon-cmake",
            "python3-colcon-package-selection",
            "python3-colcon-python-setup-py",
            "python3-colcon-parallel-executor",
        }

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            "AMENT_PYTHON_EXECUTABLE": "/usr/bin/python3",
            "COLCON_PYTHON_EXECUTABLE": "/usr/bin/python3",
        }

    def _get_source_command(self, path: str) -> list[str]:
        """Return the command to source the environment for the colcon plugin.

        Child classes that need to override this could extend or override the returned
        list.
        """
        return [
            f'if [ -n "${{ROS_DISTRO:-}}" ] && [ -f "{path}/opt/ros/${{ROS_DISTRO:-}}/local_setup.sh" ]; then',
            'AMENT_CURRENT_PREFIX="{wspath}" . "{wspath}/local_setup.sh"'.format(
                wspath=f"{path}/opt/ros/${{ROS_DISTRO:-}}"
            ),
            "fi",
        ]

    def _get_workspace_activation_commands(self) -> list[str]:
        """Return a list of commands to source a colcon workspace."""
        activation_commands: list[str] = []
        #
        # Source colcon ws in stage-snaps next
        activation_commands.append(
            "##[craft-parts.colcon] Sourcing colcon ws in stage snaps"
        )
        activation_commands.extend(self._get_source_command("${CRAFT_PART_INSTALL}"))
        activation_commands.append("")

        activation_commands.append(
            "##[craft-parts.colcon] Sourcing the colcon workspace"
        )
        activation_commands.extend(self._get_source_command(""))
        activation_commands.append("")

        return activation_commands

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        return (
            self._get_workspace_activation_commands()
            + self._get_build_commands()
            + self._get_post_build_commands()
        )

    def _get_build_commands(self) -> list[str]:
        options = cast(ColconPluginProperties, self._options)
        build_command = [
            "colcon",
            "build",
            "--base-paths",
            f'"{self._part_info.part_src_dir}"',
            "--build-base",
            f'"{self._part_info.part_build_dir}"',
            "--merge-install",
            "--install-base",
            self._get_install_path().as_posix(),
        ]

        if options.colcon_packages_ignore:
            build_command.extend(["--packages-ignore", *options.colcon_packages_ignore])

        if options.colcon_packages:
            build_command.extend(["--packages-select", *options.colcon_packages])

        # compile in release only if user did not set the build type in cmake-args
        if not any("-DCMAKE_BUILD_TYPE=" in s for s in options.colcon_cmake_args):
            build_command.extend(
                [
                    "--cmake-args",
                    "-DCMAKE_BUILD_TYPE=Release",
                    *options.colcon_cmake_args,
                ]
            )
        elif len(options.colcon_cmake_args) > 0:
            build_command.extend(["--cmake-args", *options.colcon_cmake_args])

        # Specify the number of workers
        build_command.extend(
            ["--parallel-workers", f"{self._part_info.parallel_build_count}"]
        )

        return [" ".join(build_command)]

    def _get_post_build_commands(self) -> list[str]:
        """Return a list of commands to run during the post-build step."""
        return []

    def _get_install_path(self) -> pathlib.Path:
        """Return the install path for the colcon plugin.

        Child classes that need to override this should extend the returned path.
        """
        return pathlib.Path(self._part_info.part_install_dir)
