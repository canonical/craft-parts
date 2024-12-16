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

"""The poetry plugin."""

import pathlib
import shlex
import subprocess
from typing import Literal

import pydantic
from overrides import override

from craft_parts.plugins import validator

from .base import BasePythonPlugin
from .properties import PluginProperties


class PoetryPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the poetry plugin."""

    plugin: Literal["poetry"] = "poetry"

    poetry_with: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional dependency groups",
        description="optional dependency groups to include when installing.",
    )
    poetry_export_extra_args: list[str] = pydantic.Field(
        default_factory=list,
        title="Extra arguments for poetry export",
        description="extra arguments to pass to poetry export when creating requirements.txt.",
    )
    poetry_pip_extra_args: list[str] = pydantic.Field(
        default_factory=list,
        title="Extra arguments for pip install",
        description="extra arguments to pass to pip install installing dependencies.",
    )

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class PoetryPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Poetry plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    _options: PoetryPluginProperties

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build Poetry applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
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
        if (
            not self._system_has_poetry()
            and "poetry-deps" not in self._part_info.part_dependencies
        ):
            build_packages |= {"python3-poetry"}
        return build_packages

    def _get_poetry_export_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for exporting from poetry.

        Application-specific classes may override this if they need to export from
        poetry differently.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the export script.
        """
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
        export_command.extend(self._options.poetry_export_extra_args)

        return [shlex.join(export_command)]

    def _get_pip_install_commands(self, requirements_path: pathlib.Path) -> list[str]:
        """Get the commands for installing with pip.

        Application-specific classes my override this if they need to install
        differently.

        :param requirements_path: The path of the requirements.txt file to write to.
        :returns: A list of strings forming the install script.
        """
        pip = self._get_pip()
        pip_extra_args = shlex.join(self._options.poetry_pip_extra_args)
        return [
            # These steps need to be separate because poetry export defaults to including
            # hashes, which don't work with installing from a directory.
            f"{pip} install {pip_extra_args} --requirement={requirements_path}",
            # All dependencies should be installed through the requirements file made by
            # poetry.
            f"{pip} install --no-deps .",
            # Check that the virtualenv is consistent.
            f"{pip} check",
        ]

    @override
    def _get_package_install_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        requirements_path = self._part_info.part_build_dir / "requirements.txt"

        return [
            *self._get_poetry_export_commands(requirements_path),
            *self._get_pip_install_commands(requirements_path),
        ]
