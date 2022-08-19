# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2022 Canonical Ltd.
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

"""The cmake plugin."""

from typing import Any, Dict, List, Set, cast

from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties


class CMakePluginProperties(PluginProperties, PluginModel):
    """The part properties used by the cmake plugin."""

    cmake_parameters: List[str] = []
    cmake_generator: str = "Unix Makefiles"

    # part properties required by the plugin
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="cmake", required=["source"]
        )
        return cls(**plugin_data)


class CMakePlugin(Plugin):
    """The cmake plugin is useful for building cmake based parts.

    These are projects that have a CMakeLists.txt that drives the build.
    The plugin requires a CMakeLists.txt in the root of the source tree.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    This implementation follows the syntax and behavior used in the
    Snapcraft cmake plugin for core20. Unlike the cmake plugin used for
    core18, ``CMAKE_INSTALL_PREFIX`` is not automatically set. To retain
    compatibility with the Snapcraft core18 plugin, define the cmake
    parameter ``-DCMAKE_INSTALL_PREFIX=`` in your project.  This also
    allows libraries built using the cmake plugin and staged by a different
    part to be automatically recognized without defining additional
    parameters such as ``CMAKE_INCLUDE_PATH`` or ``CMAKE_INSTALL_PATH``.

    This plugin uses the following plugin-specific keywords:

        - cmake-parameters
          (list of strings)
          parameters to pass to the build using the common cmake semantics.

        - cmake-generator
          (string; default: "Unix Makefiles")
          Determine what native build system is to be used.
          Can be either `Ninja` or `Unix Makefiles` (default).
    """

    properties_class = CMakePluginProperties

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        build_packages = {"gcc", "cmake"}

        options = cast(CMakePluginProperties, self._options)

        if options.cmake_generator == "Ninja":
            build_packages.add("ninja-build")

        return build_packages

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            # Also look for staged headers and libraries.
            "CMAKE_PREFIX_PATH": str(self._part_info.stage_dir)
        }

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(CMakePluginProperties, self._options)

        cmake_command = [
            "cmake",
            f'"{self._part_info.part_src_subdir}"',
            "-G",
            f'"{options.cmake_generator}"',
        ] + options.cmake_parameters

        return [
            " ".join(cmake_command),
            f"cmake --build . -- -j{self._part_info.parallel_build_count}",
            (
                f'DESTDIR="{self._part_info.part_install_dir}"'
                " cmake --build . --target install"
            ),
        ]

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True
