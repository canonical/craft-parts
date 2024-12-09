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
import shutil
from typing import Literal, cast

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
        title="Optional dependency groups",
        description="Optional dependency groups to include when installing.",
    )

    uv_install_packages: set[str] = pydantic.Field(
        default={'"${CRAFT_PART_NAME}"'},
        title="Optional install packages",
        description="Optional list of python packages to build and install as the final product.",
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
        uv = shutil.which("uv")
        # Guaranteed not-none by the validator class, which already asserted uv
        # was installed
        return cast(str, uv)

    @override
    def _get_pip(self) -> str:
        return f"{self._get_uv()} pip"

    def _get_create_venv_commands(self) -> list[str]:
        return [f'{self._get_uv()} venv --relocatable "${{CRAFT_PART_INSTALL}}']

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"

        sync_command = [
            self._get_uv(),
            "sync",
            "--no-dev",
            "--no-editable",
            "--python",
            '"${{CRAFT_PART_INSTALL}}/bin/python"',
            "-r",
            requirements_path.resolve(),
            *[f' --extra "{extra}"' for extra in self._options.uv_extras],
        ]

        install_commands = [shlex.join(sync_command)]

        install_commands.extend([
            f'{self._get_pip()} install --python "${{CRAFT_PART_INSTALL}}" "{package} @ ${{CRAFT_PART_BUILD}}"'
            for package in self._options.uv_install_packages
        ])

        return install_commands

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        build_environment = super().get_build_environment()
        build_environment["UV_FROZEN"] = "true"
        build_environment["UV_PYTHON_DOWNLOADS"] = "never"
        build_environment["UV_PROJECT_ENVIRONMENT"] = str(
            self._get_venv_directory().resolve()
        )
        build_environment["UV_PYTHON"] = '"${PARTS_PYTHON_INTERPRETER}"'
        build_environment["UV_PYTHON_PREFERENCE"] = "only-system"
        return build_environment
