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

"""The python plugin."""

import shlex
import shutil
import subprocess
from typing import Literal

import pydantic
from overrides import override

from craft_parts import errors
from craft_parts.plugins import validator

from .base import BasePythonPlugin
from .properties import PluginProperties


class PoetryPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the python plugin."""

    plugin: Literal["poetry"] = "poetry"

    poetry_with: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional dependency groups",
        description="optional dependency groups to include when installing.",
    )

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class PoetryPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Rust plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    _options: PoetryPluginProperties

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build Rust applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        if shutil.which("python3") is None:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason="cannot find a python3 executable on the system",
            )
        if "poetry-deps" in (part_dependencies or ()):
            self.validate_dependency(
                dependency="poetry",
                plugin_name=self._options.plugin,
                part_dependencies=part_dependencies,
            )


class PoetryPlugin(BasePythonPlugin):
    """A plugin to build python parts."""

    properties_class = PoetryPluginProperties
    validator_class = PoetryPluginEnvironmentValidator
    _options: PoetryPluginProperties

    def _system_has_poetry(self) -> bool:
        try:
            poetry_version = subprocess.check_output(["poetry", "--version"], text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        return "Poetry" in poetry_version

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        build_packages = super().get_build_packages()
        if not self._system_has_poetry():
            build_packages |= {"python3-poetry"}
        return build_packages

    def _get_pip_command(self) -> str:
        """Get the pip command for installing the package and its dependencies."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"
        return f"{self._get_pip()} install --requirement={requirements_path} ."

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"

        export_command = [
            "poetry",
            "export",
            "--format=requirements.txt",
            f"--output={requirements_path}",
            "--with-credentials",
        ]
        if self._options.poetry_with:
            export_command.append(
                f"--with={','.join(sorted(self._options.poetry_with))}",
            )

        return [
            shlex.join(export_command),
            self._get_pip_command(),
        ]
