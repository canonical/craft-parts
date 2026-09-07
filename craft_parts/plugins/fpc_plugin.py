# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
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

"""The Free Pascal plugin."""

import re
import shlex
from typing import Literal, cast

import pydantic
from typing_extensions import override

from craft_parts import errors
from craft_parts.constraints import UniqueList

from . import validator
from .base import Plugin
from .properties import PluginProperties

_VERSION_PATTERN = re.compile(r"^\d+\.\d+")


class FpcPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Free Pascal plugin."""

    plugin: Literal["fpc"] = "fpc"

    fpc_programs: UniqueList[str] = pydantic.Field(min_length=1)
    fpc_unit_paths: UniqueList[str] = []
    fpc_include_paths: UniqueList[str] = []
    fpc_parameters: list[str] = []

    # part properties required by the plugin
    source: str


class FpcPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Free Pascal plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If fpc is invalid
          and there are no parts named fpc-deps.
        """
        version = self.validate_dependency(
            dependency="fpc",
            plugin_name="fpc",
            part_dependencies=part_dependencies,
            argument="-iV",
        )
        if not _VERSION_PATTERN.match(version) and (
            part_dependencies is None or "fpc-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid fpc compiler version {version!r}",
            )


class FpcPlugin(Plugin):
    """A plugin for programs written in Free Pascal.

    The fpc plugin requires the Free Pascal compiler installed on your system.
    This can be achieved by adding the ``fpc`` package to ``build-packages``,
    or to have it installed or built in a different part. In this case, the
    name of the part supplying the compiler must be "fpc-deps".

    The fpc plugin uses the common plugin keys as well as those for "sources".
    Additionally, the following plugin-specific keys can be used:

    - ``fpc-programs``
      (list of strings)
      Source files of the programs to compile, relative to the source directory.
      Each entry produces one executable named after its source file.
    - ``fpc-unit-paths``
      (list of strings)
      Directories to search for units, relative to the source directory.
      Default is not to add any unit search paths.
    - ``fpc-include-paths``
      (list of strings)
      Directories to search for include files, relative to the source directory.
      Default is not to add any include search paths.
    - ``fpc-parameters``
      (list of strings)
      Additional parameters to pass to the compiler. Default is not to pass any.
    """

    properties_class = FpcPluginProperties
    validator_class = FpcPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(FpcPluginProperties, self._options)

        bin_dir = self._part_info.part_install_dir / "bin"
        unit_dir = self._part_info.part_build_subdir / ".parts" / "units"

        # user parameters go last so they can override the generated ones
        compiler = " ".join(
            [
                "fpc",
                *(f"-Fu{shlex.quote(path)}" for path in options.fpc_unit_paths),
                *(f"-Fi{shlex.quote(path)}" for path in options.fpc_include_paths),
                f"-FU{shlex.quote(str(unit_dir))}",
                f"-FE{shlex.quote(str(bin_dir))}",
                *options.fpc_parameters,
            ]
        )

        return [
            f"mkdir -p {shlex.quote(str(unit_dir))} {shlex.quote(str(bin_dir))}",
            *(f"{compiler} {shlex.quote(program)}" for program in options.fpc_programs),
        ]
