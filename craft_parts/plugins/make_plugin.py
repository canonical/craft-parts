# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021,2024 Canonical Ltd.
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

"""The make plugin implementation."""

from typing import Literal, cast

from overrides import override

from .base import Plugin
from .properties import PluginProperties


class MakePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the make plugin."""

    plugin: Literal["make"] = "make"

    make_parameters: list[str] = []

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class MakePlugin(Plugin):
    """A plugin useful for building make-based parts.

    Make-based projects are projects that have a Makefile that drives the
    build.

    This plugin always runs 'make' followed by 'make install', except when
    the 'artifacts' keyword is used.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

        - make-parameters
          (list of strings)
          Pass the given parameters to the make command.
    """

    properties_class = MakePluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"gcc", "make"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def _get_make_command(self, target: str = "") -> str:
        cmd = ["make", f'-j"{self._part_info.parallel_build_count}"']

        if target:
            cmd.append(target)

        options = cast(MakePluginProperties, self._options)
        cmd.extend(options.make_parameters)

        return " ".join(cmd)

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        return [
            self._get_make_command(),
            f"{self._get_make_command(target='install')} "
            f'DESTDIR="{self._part_info.part_install_dir}"',
        ]
