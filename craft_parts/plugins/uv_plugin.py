# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

from .base import BasePythonPlugin
from .properties import PluginProperties
from typing import Literal, Annotated
from pathlib import Path
from overrides import override
from .validator import PluginEnvironmentValidator
import subprocess
from craft_parts.errors import PluginEnvironmentValidationError
import pydantic
import shlex

class UvPluginProperties(PluginProperties, frozen=True):
    plugin: Literal["uv"] = "uv"
    uv_extra: set[str] = pydantic.Field(
        default_factory=set,
        title="Optional dependency groups",
        description="Optional dependency groups to include when installing.",
    )

    source: str  # pyright: ignore[reportGeneralTypeIssues]

class UvPluginEnvironmentValidator(PluginEnvironmentValidator):
    _options: UvPluginProperties

    @override
    def validate_environment(self, *, part_dependencies: list[str] | None = None) -> None:
        version = self.validate_dependency(
            dependency="uv",
            plugin_name=self._options.plugin,
            part_dependencies=part_dependencies,
            argument="--version",
        )
        if not version.startswith("uv") and (
            part_dependencies is None or "go-deps" not in part_dependencies
        ):
            raise PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid uv version {version!r}",
            )

class UvPlugin(BasePythonPlugin):
    properties_class = UvPluginProperties
    validator_class = UvPluginEnvironmentValidator
    _options: UvPluginProperties
    
    def _system_has_uv(self) -> bool:
        try:
            uv_version = subprocess.check_output(["uv", "--version"], text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        return "uv" in uv_version
    
    def _get_uv_export_commands(self, requirements_path: Path) -> list[str]:
        export_command = [
            "uv",
            "export",
            "--format=requirements-txt",
            f"--output={requirements_path}",
            # Requires uv.lock exists and is up to date
            "--locked",
        ]

        if self._options.uv_extra:
            export_command.append(f"--with={','.join(sorted(self._options.uv_extra))}")

        return [shlex.join(export_command)]
    
    def _get_pip_install_commands(self, requirements_path: Path) -> list[str]:
        pip = self._get_pip()
        return [
            f"{pip} install --requirement={requirements_path}",
            f"{pip} install --no-deps .",
            f"{pip} check",
        ]

    def _get_package_install_commands(self) -> list[str]:
        requirements_path = self._part_info.part_build_dir / "requirements.txt"
        return [
            *self._get_uv_export_commands(requirements_path),
            *self._get_pip_install_commands(requirements_path),
        ]

