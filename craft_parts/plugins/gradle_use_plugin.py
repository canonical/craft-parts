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

"""The gradle-use plugin."""

import shlex
from pathlib import Path
from typing import Literal, cast

from typing_extensions import override

from craft_parts.utils.gradle_utils import PUBLISH_BLOCK_TEMPLATE

from .gradle_plugin import GradlePlugin
from .properties import PluginProperties


class GradleUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the gradle plugin.

    - gradle_init_script:
      (string)
      The path to init script to run before build script is executed.
    - gradle_parameters:
      (list of strings)
      Extra arguments to pass along to Gradle task execution.
    - gradle_use_daemon:
      (boolean)
      Whether to use the Gradle daemon during the build.
    """

    plugin: Literal["gradle-use"] = "gradle-use"
    gradle_init_script: str = ""
    gradle_parameters: list[str] = []
    gradle_use_daemon: bool = False

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class GradleUsePlugin(GradlePlugin):
    """A plugin to publish Gradle artifacts to a local Maven repository.

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

    - gradle-init-script:
      (string)
      Path to the Gradle init script to use during build task execution.
    - gradle-parameters:
      (list of strings)
      Flags to pass to the build using the gradle semantics for parameters.
    - gradle-use-daemon:
      (boolean, default False)
      Whether to use the Gradle daemon during the build.
    """

    properties_class = GradleUsePluginProperties  # type: ignore[assignment]

    @property
    def _publish_maven_repo(self) -> Path:
        """Path to local Maven repository for publishing."""
        return self._part_info.part_export_dir / "maven-use"

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        options = cast(GradleUsePluginProperties, self._options)

        self._setup_proxy()

        extra_args: list[str] = [
            "--init-script",
            self._create_publish_init_script(),
        ]

        if options.gradle_init_script:
            extra_args.extend(["--init-script", options.gradle_init_script])

        if self._is_self_contained():
            extra_args.extend(
                [
                    "--offline",
                    "--init-script",
                    self._create_self_contained_init_script(),
                ]
            )

        if not options.gradle_use_daemon:
            extra_args.append("--no-daemon")

        gradle_cmd = shlex.join(
            [
                self.gradle_executable,
                "publish",
                *extra_args,
                *options.gradle_parameters,
            ]
        )

        return [
            gradle_cmd,
            # remove gradle-wrapper.jar files included in the project if any.
            f'find {self._part_info.part_build_subdir} -name "gradle-wrapper.jar" -type f -delete',
        ]

    def _create_publish_init_script(self) -> str:
        init_script = (
            self._part_info.part_build_subdir / ".parts" / "publish.init.gradle"
        )
        init_script.parent.mkdir(parents=True, exist_ok=True)
        init_script.write_text(
            PUBLISH_BLOCK_TEMPLATE.format(
                publish_maven_repo=self._publish_maven_repo.as_uri()
            )
        )
        return str(init_script)
