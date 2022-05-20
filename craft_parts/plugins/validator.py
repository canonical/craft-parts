# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Definitions and helpers for plugin environment validation."""

import logging
import subprocess
import tempfile
from typing import List, Optional

from craft_parts import errors

from .properties import PluginProperties

logger = logging.getLogger(__name__)


COMMAND_NOT_FOUND = 127
"""The shell error code for command not found."""


class PluginEnvironmentValidator:
    """Base class for plugin environment validators.

    Plugins may require certain environment elements to be present in
    order to build a part, regardless of how these elements were installed
    on the system. For example, a compiler may have been installed from a
    deb package, a snap, built from sources or even built by a different
    part. Plugin environment validators allow a plugin to ensure its
    execution environment is correct before building a part.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def __init__(self, *, part_name: str, env: str, properties: PluginProperties):
        self._part_name = part_name
        self._env = env
        self._options = properties

    def validate_environment(
        self, *, part_dependencies: Optional[List[str]] = None
    ) -> None:
        """Ensure the plugin execution environment is valid.

        The environment is verified twice: during the execution prologue after
        build packages and snaps are installed (to provide an early error message
        if the environment is invalid), and before running the build step for the
        part. During the prologue validation the environment may be incomplete,
        so we pass a list of the part dependencies as a hint of which parts may
        be used to build the environment.

        :param part_dependencies: A list of the parts this part depends on, so
            the validator can check if the required environment elements are
            supplied by another part when the method is called from the execution
            prologue. If the validation fails and list is empty, the error is
            final (the missing elements can't be supplied by a different part).
            The plugin may require a specific part name as a hint that the
            part will attempt to supply missing environment elements.

        :raises PluginEnvironmentValidationError: If the environment is invalid.
        """

    def validate_dependency(
        self,
        dependency: str,
        plugin_name: str,
        part_dependencies: Optional[List[str]],
        argument: str = "--version",
    ) -> str:
        """Validate that the environment has a required dependency.

        `<dependency-name> --version` is executed to confirm the dependency is valid.

        :param dependency: name of the dependency to validate.
        :param plugin_name: used to generate the part name that would satisfy
                            the dependency.
        :param part_dependencies: A list of the parts this part depends on.
        :param argument: argument to call with the dependency. Default is `--version`.

        :raises PluginEnvironmentValidationError: If the environment is invalid.

        :return: output from executed dependency
        """
        try:
            command = f"{dependency} {argument}"
            output = self._execute(command).strip()
            logger.debug("executed %s with output %s", command, output)
            return output
        except subprocess.CalledProcessError as err:
            if err.returncode != COMMAND_NOT_FOUND:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"{dependency!r} failed with error code {err.returncode}",
                ) from err

            if part_dependencies is None:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=f"{dependency!r} not found",
                ) from err

            part_dependency = f"{plugin_name}-deps"
            if part_dependency not in part_dependencies:
                raise errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason=(
                        f"{dependency!r} not found and part {self._part_name!r} "
                        f"does not depend on a part named {part_dependency!r} "
                        "that would satisfy the dependency"
                    ),
                ) from err
        return ""

    def _execute(self, cmd: str) -> str:
        """Execute a command in a build environment shell.

        :param cmd: The command to execute.

        :return: The command output or error message.
        """
        logger.debug("plugin validation environment: %s", self._env)
        logger.debug("plugin validation command: %r", cmd)

        with tempfile.NamedTemporaryFile(mode="w+") as env_file:
            print(self._env, file=env_file)
            print(cmd, file=env_file)
            env_file.flush()

            proc = subprocess.run(
                ["/bin/bash", env_file.name],
                check=True,
                capture_output=True,
                universal_newlines=True,
            )

        return proc.stderr if proc.stderr else proc.stdout
