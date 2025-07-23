# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""A craft-parts plugin for building projects with the Bazel build system."""

import shutil
from typing import Literal, cast

from overrides import override
from pydantic import model_validator
from typing_extensions import Self

from craft_parts import plugins
from craft_parts.plugins.properties import PluginProperties

from . import validator

# The files that officially mark the root of a Bazel workspace.
# BAZEL_MARKER_FILES = {"MODULE.bazel", "REPO.bazel", "WORKSPACE.bazel", "WORKSPACE"}


class BazelPluginProperties(PluginProperties, frozen=True):
    """Properties for the Bazel plugin."""
    plugin: Literal["bazel"] = "bazel"
    source: str | None = None  # for compatibility with base

    bazel_targets: list[str] = ["//..."]
    bazel_options: list[str] = []
    bazel_command: str = "build"  # One of 'build', 'test', 'run'
    # bazel_startup_options: list[str] = []  # Uncomment to enable startup options in the future
    
    @model_validator(mode="after")
    def gradle_task_defined(self) -> Self:
        """Bazel command must be defined.

        This check ensures that the user does not override the default value "build/test/run" with an
        empty string.
        """
        if not self.bazel_command:
            raise ValueError("bazel_command must be defined")
        return self


class BazelPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check that 'bazel' or 'bazelisk' is available in the environment."""
    def validate_environment(self, *, part_dependencies: list[str] | None = None) -> None:
        # Try bazel first, then bazelisk
        for dep, plugin in [("bazel", "bazel"), ("bazelisk", "bazel")]:
            version = self.validate_dependency(
                dependency=dep,
                plugin_name=plugin,
                part_dependencies=part_dependencies,
                argument="--version",
            )
            if version:
                return
        raise RuntimeError(
            "Neither 'bazel' nor 'bazelisk' was found in the environment. Please install Bazel (https://bazel.build) or Bazelisk (https://github.com/bazelbuild/bazelisk) and ensure it is in your PATH."
        )


class BazelPlugin(plugins.Plugin):
    """A plugin for building projects with the Bazel build system."""
    properties_class = BazelPluginProperties
    validator_class = BazelPluginEnvironmentValidator

    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        # Propagate proxy variables if present
        import os
        env = {}
        for var in ["http_proxy", "https_proxy", "no_proxy"]:
            if var in os.environ:
                env[var] = os.environ[var]
        return env

    # @classmethod
    # @override
    # def get_out_of_source_build(cls) -> bool:
    #     return True

    @override
    def get_build_commands(self) -> list[str]:
        opts = cast(BazelPluginProperties, self._options)
        executable = "bazel"  # Use 'bazel' by default
        # startup_opts = opts.bazel_startup_options if hasattr(opts, 'bazel_startup_options') else []
        # startup_opts_str = " ".join(startup_opts)
        options_str = " ".join(opts.bazel_options)
        targets_str = " ".join(opts.bazel_targets)
        # cmd = f"{executable} {startup_opts_str} {opts.bazel_command} {options_str} {targets_str}".strip()
        cmd = f"{executable} {opts.bazel_command} {options_str} {targets_str}".strip()
        return [cmd]