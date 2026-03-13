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

from typing_extensions import override

from craft_parts.utils.npm_utils import get_install_from_local_tarballs_commands

from .npm_plugin import NpmPlugin


class NpmUsePlugin(NpmPlugin):
    """A plugin to pack npm packages to a local shared cache.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.
    """

    @property
    def _npm_cache_export(self) -> Path:
        """Path to npm pack destination."""
        return self._part_info.part_export_dir / "npm-cache"

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

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
