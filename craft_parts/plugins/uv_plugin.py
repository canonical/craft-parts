# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2024 Canonical Ltd.
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

"""The uv plugin."""

import shlex
from typing import Literal

import pydantic
from overrides import override

from craft_parts import errors
from craft_parts.plugins import validator

from .base import BasePythonPlugin
from .properties import PluginProperties


class UvPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the uv plugin."""

    plugin: Literal["uv"] = "uv"

    uv_extras: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional extra dependencies",
        description="Optional extra dependencies to include when installing.",
    )

    uv_groups: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional dependency groups",
        description="Optional dependency groups to include when installing.",
    )

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class UvPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the uv plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    _options: UvPluginProperties

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build uv applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        version = self.validate_dependency(
            dependency="uv",
            plugin_name=self._options.plugin,
            part_dependencies=part_dependencies,
            argument="version",
        )
        if not version.startswith("uv") and (
            part_dependencies is None or "uv-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid uv version {version!r}",
            )


class UvPlugin(BasePythonPlugin):
    """A plugin to build python parts."""

    properties_class = UvPluginProperties
    validator_class = UvPluginEnvironmentValidator
    _options: UvPluginProperties

    @override
    def _get_pip(self) -> str:
        return "uv pip"

    @override
    def _get_rewrite_shebangs_commands(self) -> list[str]:
        return []

    def _get_create_venv_commands(self) -> list[str]:
        return [
            f'uv venv --relocatable --allow-existing --python "{self._get_system_python_interpreter()}" "{self._get_venv_directory()}"',
            f'PARTS_PYTHON_VENV_INTERP_PATH="{self._get_venv_directory()}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        ]

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        sync_command = [
            "uv",
            "sync",
            "--no-dev",
            "--no-editable",
        ]

        for extra in sorted(self._options.uv_extras):
            sync_command.extend(["--extra", extra])
        for group in sorted(self._options.uv_groups):
            sync_command.extend(["--group", group])

        return [shlex.join(sync_command)]

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        venv_dir = str(self._get_venv_directory().resolve())
        return super().get_build_environment() | {
            "VIRTUAL_ENV": venv_dir,
            "UV_PROJECT_ENVIRONMENT": venv_dir,
            "UV_FROZEN": "true",
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_PYTHON": '"${PARTS_PYTHON_INTERPRETER}"',
            "UV_PYTHON_PREFERENCE": "only-system",
        }
