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

import pathlib
import shlex
import subprocess
from typing import Literal

import pydantic
from overrides import override

from craft_parts.plugins import validator
from craft_parts import errors

from .base import BasePythonPlugin
from .properties import PluginProperties


class UvPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the uv plugin."""

    plugin: Literal["uv"] = "uv"

    uv_extras: set[str] = pydantic.Field(
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
    
    def _get_uv(self) -> str:
        return f'"${{HOME}}/.cargo/bin/uv'
    
    @override
    def _get_pip(self) -> str:
        return f"{self._get_uv()} pip"

    def _get_uv_export_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for exporting from uv.

        Application-specific classes may override this if they need to export from
        uv differently.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the export script.
        """
        export_command = [
            "uv",
            "export",
            "--no-dev",
            "--format=requirements.txt",
            f"--output={requirements_path}",
        ]
        if self._options.uv_extras:
            for extra in self._options.uv_extras:
                export_command.append(
                    f"--extra={extra}",
                )

        return [shlex.join(export_command)]
    
    def _get_create_venv_commands(self) -> list[str]:
        return [f'{self._get_uv()} venv --relocatable "${{CRAFT_PART_INSTALL}}']

    def _get_pip_install_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for installing with pip.

        Application-specific classes my override this if they need to install
        differently.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the install script.
        """
        pip = self._get_pip()
        return [
            f'{pip} install --python "${{CRAFT_PART_INSTALL}}/bin/python -r {requirements_path.resolve()}',
            f'{pip} install --python "${{CRAFT_PART_INSTALL}} "${{CRAFT_PART_NAME}} @ ${{CRAFT_PART_BUILD}}'
        ]

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"

        return [
            *self._get_uv_export_commands(requirements_path),
            *self._get_pip_install_commands(requirements_path),
        ]
    
    @override
    def get_build_environment(self) -> dict[str, str]:
        build_environment = super().get_build_environment()
        build_environment["UV_FROZEN"] = "1"
        build_environment["UV_PYTHON_DOWNLOADS"] = "never"
        return build_environment
