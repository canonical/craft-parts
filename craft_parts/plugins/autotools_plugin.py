# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020 Canonical Ltd.
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

"""The autotools plugin implementation."""

from typing import Any, Dict, List, Set, cast

from overrides import override

from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties


class AutotoolsPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the autotools plugin."""

    autotools_configure_parameters: List[str] = []
    autotools_bootstrap_parameters: List[str] = []

    # part properties required by the plugin
    source: str

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "AutotoolsPluginProperties":
        """Populate autotools properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="autotools", required=["source"]
        )
        return cls(**plugin_data)


class AutotoolsPlugin(Plugin):
    """The autotools plugin is used for autotools-based parts.

    Autotools-based projects are the ones that have the usual
    `./configure && make && make install` instruction set.

    This plugin will check for the existence of a 'configure' file, if one
    cannot be found, it will first try to run 'autogen.sh' or 'bootstrap'
    to generate one.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    In addition, this plugin uses the following plugin-specific keywords:

        - autotools-bootstrap-parameters
          (list of strings)
          bootstrap flags to pass to the build if a bootstrap file is found in
          the project. These can in some cases be seen by running
          './bootstrap --help'

        - autotools-configure-parameters
          (list of strings)
          configure flags to pass to the build such as those shown by running
          './configure --help'
    """

    properties_class = AutotoolsPluginProperties

    @override
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"autoconf", "automake", "autopoint", "gcc", "libtool"}

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def _get_configure_command(self) -> str:
        options = cast(AutotoolsPluginProperties, self._options)
        cmd = ["./configure", *options.autotools_configure_parameters]
        return " ".join(cmd)

    def _get_bootstrap_command(self) -> str:
        options = cast(AutotoolsPluginProperties, self._options)
        cmd = [
            "env",
            "NOCONFIGURE=1",
            "./bootstrap",
            *options.autotools_bootstrap_parameters,
        ]
        return " ".join(cmd)

    # pylint: disable=line-too-long

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        return [
            "[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh",
            f"[ ! -f ./configure ] && [ -f ./bootstrap ] && {self._get_bootstrap_command()}",
            "[ ! -f ./configure ] && autoreconf --install",
            self._get_configure_command(),
            f"make -j{self._part_info.parallel_build_count}",
            f'make install DESTDIR="{self._part_info.part_install_dir}"',
        ]
