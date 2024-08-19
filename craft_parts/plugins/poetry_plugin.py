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
from textwrap import dedent
from typing import Literal, cast

from overrides import override
import pydantic

from craft_parts import errors
from craft_parts.plugins import validator

from .base import BasePythonPlugin, Plugin
from .properties import PluginProperties


class PoetryPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the python plugin."""

    plugin: Literal["poetry"] = "poetry"

    poetry_with: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional dependency groups",
        description="optional dependency groups to include when installing."
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
                reason="cannot find a python3 executable on the system"
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

    # pylint: disable=line-too-long

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        build_commands = self._get_venv_commands()

        venv_python = f"{self._part_info.part_install_dir}/bin/python"
        pip = f"{self._part_info.part_install_dir}/bin/pip"

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
        build_commands.append(shlex.join(export_command))

        build_commands.append(
            f"{pip} install --requirement {requirements_path} ."
        )

        # Now fix shebangs.
        script_interpreter = self._get_script_interpreter()
        build_commands.append(
            dedent(
                f"""\
                find "{self._part_info.part_install_dir}" -type f -executable -print0 | xargs -0 \\
                    sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|{script_interpreter}|"
                """
            )
        )
        # Find the "real" python3 interpreter.
        build_commands.append(self._get_find_python_interpreter_script())

        # Handle the venv symlink (either remove it or set the final correct target)
        if self._should_remove_symlinks():
            build_commands.append(
                f"echo Removing python symlinks in {self._part_info.part_install_dir}/bin"
            )
            build_commands.append(
                f'rm "{self._part_info.part_install_dir}"/bin/python*'
            )
        else:
            build_commands.append(
                'ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"'
            )

        return build_commands

