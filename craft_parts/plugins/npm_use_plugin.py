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

"""The npm-use plugin."""

from pathlib import Path
from typing import Literal

from typing_extensions import override

from craft_parts.utils.npm_utils import get_install_from_local_tarballs_commands

from . import validator
from .plugins import Plugin
from .properties import PluginProperties


class NpmUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the npm plugin."""

    plugin: Literal["npm-use"] = "npm-use"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class NpmUsePluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the npm plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build npm applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        for dependency in ["node", "npm"]:
            self.validate_dependency(
                dependency=dependency,
                plugin_name="npm",
                part_dependencies=part_dependencies,
            )


class NpmUsePlugin(Plugin):
    """A plugin to pack npm packages to a local shared cache.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.
    """

    properties_class = NpmUsePluginProperties
    validator_class = NpmUsePluginEnvironmentValidator

    @property
    def _is_self_contained(self) -> bool:
        return "self-contained" in self._part_info.build_attributes

    @property
    def _npm_cache_export(self) -> Path:
        """Path to npm pack destination."""
        return self._part_info.part_export_dir / "npm-cache"

    @property
    def _npm_cache_backstage(self) -> Path:
        """Path to npm cache to consume packages from."""
        return self._part_info.project_info.dirs.backstage_dir / "npm-cache"

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
        # set the Node environment to production mode
        base_env = {
            "NODE_ENV": "production",
        }

        if self._is_self_contained:
            # explicitly block registry access during offline builds
            base_env["npm_config_registry"] = "https://localhost:1"

        return base_env

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        return []

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        self._npm_cache_export.mkdir(parents=True, exist_ok=True)
        pkg_path = self._part_info.part_build_dir / "package.json"
        bundled_pkg_path = (
            self._part_info.part_build_subdir / ".parts" / "package.bundled.json"
        )

        if self._is_self_contained:
            return [
                *get_install_from_local_tarballs_commands(
                    pkg_path, bundled_pkg_path, self._npm_cache_backstage
                ),
                f'mv "$(npm pack . | tail -1)" "{self._npm_cache_export}/"',
            ]

        return [
            f'mv "$(npm pack . | tail -1)" "{self._npm_cache_export}/"',
        ]

    @classmethod
    @override
    def supported_build_attributes(cls) -> set[str]:
        """Return the build attributes that this plugin supports."""
        return {"self-contained"}
