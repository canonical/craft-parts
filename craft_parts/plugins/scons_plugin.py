# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""The SCons plugin."""

from typing import Any, Dict, List, Optional, Set, cast

from overrides import override

from craft_parts import errors

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties


class SConsPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the SCons plugin."""

    scons_parameters: List[str] = []

    # part properties required by the plugin
    source: str

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "SConsPluginProperties":
        """Populate make properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="scons", required=["source"]
        )
        return cls(**plugin_data)


class SConsPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the SCons plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: Optional[List[str]] = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If scons is invalid
          and there are no parts named "scons-deps".
        """
        version = self.validate_dependency(
            dependency="scons",
            plugin_name="scons",
            part_dependencies=part_dependencies,
            argument="--version",
        )
        if not version.startswith("SCons by Steven Knight et al.") and (
            part_dependencies is None or "scons-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid scons compiler version {version!r}",
            )


class SConsPlugin(Plugin):
    """A plugin for SCons projects.

    The plugin needs the ``scons`` tool which can be provisioned in one of the
    following ways:

    - Add "scons" to the part's ``build-packages``;
    - Build a custom version of ``scons`` on a separate part called ``scons-deps``
      and have the part that uses this plugin depend on the ``scons-deps`` part.

    Note that other dependencies (C/C++ compiler, Java compiler, etc) must be
    declared via ``build-packages`` or otherwise provisioned.

    Since there is no "official" way of defining the target installation directory
    for SCons-built artifacts, the default build will set the DESTDIR environment
    variable which contains the root which the SConstruct file should use to
    configure its ``Install()`` builder target.

    The plugin supports the following keywords:

    - ``scons-parameters``
      (list of strings)
      Additional values to pass to the ``scons`` and ``scons install`` command
      lines.

    """

    properties_class = SConsPluginProperties
    validator_class = SConsPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            "DESTDIR": f"{self._part_info.part_install_dir}",
        }

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        options = cast(SConsPluginProperties, self._options)

        return [
            " ".join(["scons", *options.scons_parameters]),
            " ".join(["scons", "install", *options.scons_parameters]),
        ]
