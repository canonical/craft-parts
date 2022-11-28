# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

"""The Ant plugin."""

import logging
from typing import Any, Dict, List, Optional, Set, cast

from craft_parts import errors

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class AntPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the Ant plugin."""

    ant_build_targets: List[str] = []
    # go_generate: List[str] = []

    # part properties required by the plugin
    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate make properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="ant", required=["source"]
        )
        return cls(**plugin_data)


class AntPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Ant plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    def validate_environment(self, *, part_dependencies: Optional[List[str]] = None):
        """Ensure the environment contains dependencies needed by the plugin.

        :param part_dependencies: A list of the parts this part depends on.

        :raises PluginEnvironmentValidationError: If ant is invalid
        and there are no parts named ant.
        """
        version = self.validate_dependency(
            dependency="ant",
            plugin_name="ant",
            part_dependencies=part_dependencies,
            argument="-version",
        )
        if not version.startswith("Apache Ant") and (
            part_dependencies is None or "ant-deps" not in part_dependencies
        ):
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_name,
                reason=f"invalid ant version {version!r}",
            )


class AntPlugin(Plugin):
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

    properties_class = AntPluginProperties
    validator_class = AntPluginEnvironmentValidator

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        # command = ["ant"]
        # if self.options.ant_buildfile:
        #     command.extend(["-f", self.options.ant_buildfile])
        #
        # if self.options.ant_build_targets:
        #     command.extend(self.options.ant_build_targets)
        #
        # for prop, value in self.options.ant_properties.items():
        #     command.extend(["-D{}={}".format(prop, value)])
        #
        # self.run(command, rootdir=self.builddir)
        # files = glob(os.path.join(self.builddir, "target", "*.jar"))
        # if files:
        #     jardir = os.path.join(self.installdir, "jar")
        #     os.makedirs(jardir)
        #     for f in files:
        #         base = os.path.basename(f)
        #         os.link(f, os.path.join(jardir, base))
        # pylint: disable=line-too-long
        options = cast(AntPluginProperties, self._options)

        command = ["ant"]

        command.extend(options.ant_build_targets)

        # Find the "java" executable make a link to it in CRAFT_PART_INSTALL/bin/java
        link_java = [
            "java_bin=$(find ${CRAFT_PART_INSTALL} -name java -type f -executable)",
            "mkdir -p ${CRAFT_PART_INSTALL}/bin",
            "ln -s --relative $java_bin ${CRAFT_PART_INSTALL}/bin/java",
        ]
        # Find all the generated jars and hardlink them inside CRAFT_PART_INSTALL/jar/
        link_jars = [
            "mkdir -p ${CRAFT_PART_INSTALL}/jar",
            r'find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \;',
        ]

        return (
            [
                " ".join(command),
            ]
            + link_java
            + link_jars
        )
