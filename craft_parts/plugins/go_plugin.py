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

"""The Go plugin."""

import logging
import pathlib
from typing import Literal, cast

from overrides import override

from craft_parts import errors

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class GoPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Go plugin."""

    plugin: Literal["go"] = "go"

    go_buildtags: list[str] = []
    go_generate: list[str] = []

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class GoPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Go plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If go is invalid
          and there are no parts named go.
        """
        version = self.validate_dependency(
            dependency="go",
            plugin_name="go",
            part_dependencies=part_dependencies,
            argument="version",
        )
        if not version.startswith("go version") and (
            part_dependencies is None or "go-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid go compiler version {version!r}",
            )


class GoPlugin(Plugin):
    """A plugin for go projects using go.mod.

    The go plugin requires a go compiler installed on your system. This can
    be achieved by adding the appropriate golang package to ``build-packages``,
    or to have it installed or built in a different part. In this case, the
    name of the part supplying the go compiler must be "go".

    The go plugin uses the common plugin keywords as well as those for "sources".
    Additionally, the following plugin-specific keywords can be used:

    - ``go-buildtags``
      (list of strings)
      Tags to use during the go build. Default is not to use any build tags.
    - ``go-generate``
      (list of strings)
      Parameters to pass to `go generate` before building. Each item on the list
      will be a separate `go generate` call. Default is not to call `go generate`.
    """

    properties_class = GoPluginProperties
    validator_class = GoPluginEnvironmentValidator

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
        return {
            "GOBIN": f"{self._part_info.part_install_dir}/bin",
        }

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(GoPluginProperties, self._options)

        # Matches go-use plugin expectation.
        dependencies_dir: pathlib.Path = self._part_info.backstage_dir / "go-use"
        if dependencies_dir.is_dir():
            setup_cmds = [
                "go work init .",
                "go work use .",
                *(
                    f"go work use '{dependencies_dir}/{dep_part}'"
                    for dep_part in self._part_info.part_dependencies
                    if (dependencies_dir / dep_part).exists()
                ),
            ]
        else:
            setup_cmds = ["go mod download all"]

        tags = f"-tags={','.join(options.go_buildtags)}" if options.go_buildtags else ""

        generate_cmds: list[str] = [f"go generate {cmd}" for cmd in options.go_generate]

        return [
            *setup_cmds,
            *generate_cmds,
            f'go install -p "{self._part_info.parallel_build_count}" {tags} ./...',
        ]
