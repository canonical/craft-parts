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

"""The Bazel plugin implementation."""

from typing import Literal, cast

from typing_extensions import override

from .base import Plugin
from .properties import PluginProperties


class BazelPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Bazel plugin."""

    plugin: Literal["bazel"] = "bazel"

    bazel_targets: list[str] = ["//..."]
    bazel_parameters: list[str] = []

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class BazelPlugin(Plugin):
    """A plugin useful for building Bazel-based parts.

    Bazel-based projects are projects that have a Bazel build system that drives the
    build.

    This plugin runs ``bazel build`` for the configured targets and then copies
    Bazel output artifacts from ``bazel-bin`` into ``$CRAFT_PART_INSTALL``.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Plugin-specific keywords:

    ``bazel-parameters`` (list of strings) passes additional arguments to
    ``bazel build``.

    ``bazel-targets`` (list of strings; default: ["//..."]) sets which targets
    are built.
    """

    properties_class = BazelPluginProperties

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"bazel-bootstrap"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def _get_bazel_build_command(self) -> str:
        cmd = ["bazel", "build", f"--jobs={self._part_info.parallel_build_count}"]
        options = cast(BazelPluginProperties, self._options)
        cmd.extend(options.bazel_parameters)
        cmd.extend(options.bazel_targets)

        return " ".join(cmd)

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        part_install_dir = self._part_info.part_install_dir
        return [
            self._get_bazel_build_command(),
            f'mkdir -p "{part_install_dir}"',
            f'cp -a bazel-bin/. "{part_install_dir}"',
        ]
