# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2025 Canonical Ltd.
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

import subprocess
from typing import Literal, cast

from overrides import override

from . import validator
from .base import Plugin
from .properties import PluginProperties


class BazelPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Bazel plugin.

    - bazel_targets: (list of strings) Bazel build targets to build.
    - bazel_startup_options: (list of strings) Startup options for Bazel.
    - bazel_build_options: (list of strings) Build options for Bazel.
    - source: (string) The source directory or URL for the part.
    """
    plugin: Literal["bazel"] = "bazel"
    bazel_targets: list[str] = []
    bazel_startup_options: list[str] = []
    bazel_build_options: list[str] = []
    source: str | None = None  # Match base class signature

class BazelPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Bazel plugin."""
    pass

class BazelPlugin(Plugin):
    """A plugin for building projects with Bazel.

    This plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    - bazel-targets: (list of strings) Bazel build targets to build.
    - bazel-startup-options: (list of strings) Startup options for Bazel.
    - bazel-build-options: (list of strings) Build options for Bazel.
    """
    properties_class = BazelPluginProperties
    validator_class = BazelPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"bazel"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(BazelPluginProperties, self._options)
        command = [
            "bazel",
            *options.bazel_startup_options,
            "build",
            *options.bazel_build_options,
        ]
        if options.bazel_targets:
            command.append("--")
            command.extend(options.bazel_targets)
        return [" ".join(command)]