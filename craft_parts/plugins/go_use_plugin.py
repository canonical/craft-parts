# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021,2024 Canonical Ltd.
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

"""The Go Use plugin."""

import logging
import subprocess
from typing import Literal

from overrides import override

from craft_parts import errors

from .base import Plugin
from .go_plugin import GoPluginEnvironmentValidator
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class GoUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Go Use plugin."""

    plugin: Literal["go-use"] = "go-use"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class GoUsePlugin(Plugin):
    """A plugin to setup the source into a go workspace.

    The go plugin requires a go compiler installed on your system. This can
    be achieved by adding the appropriate golang package to ``build-packages``,
    or to have it installed or built in a different part. In this case, the
    name of the part supplying the go compiler must be "go".
    """

    properties_class = GoUsePluginProperties
    validator_class = GoPluginEnvironmentValidator

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True

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
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        # Set the go workspace directory to live at the root of all parts.
        workspace_dir = self._part_info.project_info.dirs.parts_dir
        workspace = workspace_dir / "go.work"

        # We do not want this implementation detail exposed in the run script
        if not workspace.exists():
            logger.debug(f"Init go workspace at {workspace}")
            try:
                subprocess.run(
                    ["go", "work", "init"],
                    capture_output=True,
                    check=True,
                    cwd=workspace_dir,
                )
            except subprocess.CalledProcessError as call_error:
                logger.debug(
                    f"Workspace init failed {call_error!r} "
                    f"stdout: {call_error.stdout!r} "
                    f"stderr: {call_error.stderr}"
                )
                raise errors.PluginBuildError(
                    part_name=self._part_info.part_name, plugin_name="go-use"
                )

        return [
            f"go work use {self._part_info.part_src_dir}",
        ]
