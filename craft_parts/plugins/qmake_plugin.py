# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
# Copyright 2023 Scarlett Moore <sgmoore@kde.org>.
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


"""The qmake plugin."""

from typing import Any, Dict, List, Set, cast

from overrides import override
from typing_extensions import Self

from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties


class QmakePluginProperties(PluginProperties, PluginModel):
    """The part properties used by the qmake plugin."""

    qmake_parameters: List[str] = []
    qmake_project_file: str = ""
    qmake_major_version: int = 5

    # part properties required by the plugin
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> Self:
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="qmake", required=["source"]
        )
        return cls(**plugin_data)


class QmakePlugin(Plugin):
    """The qmake plugin is useful for building qmake-based parts.

    These are projects that are built using .pro files.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

    - qmake-parameters:
      (list of strings)
      additional options to pass to the qmake invocation.

    - qmake-project-file:
      (string)
      the qmake project file to use. This is usually only needed if
      qmake can not determine what project file to use on its own.

    - qmake_major_version:
      (int)
      set the qt major version. This is only needed to support qt6 builds.
      Version 5 is default.
    """

    properties_class = QmakePluginProperties

    @override
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        options = cast(QmakePluginProperties, self._options)

        if options.qmake_major_version == 6:  # noqa: PLR2004 (magic value)
            build_packages = {"g++", "make", "qmake6"}
        else:
            build_packages = {"g++", "make", "qt5-qmake"}
        return build_packages

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        options = cast(QmakePluginProperties, self._options)

        if options.qmake_major_version == 6:  # noqa: PLR2004 (magic value)
            return {"QT_SELECT": "qt6"}

        return {"QT_SELECT": "qt5"}

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(QmakePluginProperties, self._options)

        if options.qmake_major_version == 6:  # noqa: PLR2004 (magic value)
            qmake_configure_command = [
                "qmake6",
                'QMAKE_CFLAGS+="${CFLAGS:-}"',
                'QMAKE_CXXFLAGS+="${CXXFLAGS:-}"',
                'QMAKE_LFLAGS+="${LDFLAGS:-}"',
                *options.qmake_parameters,
            ]
        else:
            qmake_configure_command = [
                "qmake",
                'QMAKE_CFLAGS+="${CFLAGS:-}"',
                'QMAKE_CXXFLAGS+="${CXXFLAGS:-}"',
                'QMAKE_LFLAGS+="${LDFLAGS:-}"',
                *options.qmake_parameters,
            ]

        if options.qmake_project_file:
            qmake_configure_command.append(
                str(self._part_info.part_src_dir / options.qmake_project_file)
            )
        else:
            qmake_configure_command.append(str(self._part_info.part_src_dir))

        return [
            " ".join(qmake_configure_command),
            f"env -u CFLAGS -u CXXFLAGS make -j{self._part_info.parallel_build_count}",
            f"make install INSTALL_ROOT={self._part_info.part_install_dir}",
        ]

    @classmethod
    @override
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True
