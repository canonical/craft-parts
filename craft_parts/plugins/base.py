# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2024 Canonical Ltd.
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

"""Plugin base class and definitions."""

from __future__ import annotations

import abc
from copy import deepcopy
import shutil
from typing import TYPE_CHECKING

from overrides import override

from craft_parts import errors
from craft_parts.actions import ActionProperties

from .properties import PluginProperties
from .validator import PluginEnvironmentValidator

if TYPE_CHECKING:
    # import module to avoid circular imports in sphinx doc generation
    from craft_parts import infos


class Plugin(abc.ABC):
    """The base class for plugins.

    :cvar properties_class: The plugin properties class.
    :cvar validator_class: The plugin environment validator class.

    :param part_info: The part information for the applicable part.
    :param properties: Part-defined properties.
    """

    properties_class: type[PluginProperties]
    validator_class = PluginEnvironmentValidator

    supports_strict_mode = False
    """Plugins that can run in 'strict' mode must set this classvar to True."""

    def __init__(
        self, *, properties: PluginProperties, part_info: infos.PartInfo
    ) -> None:
        self._options = properties
        self._part_info = part_info
        self._action_properties: ActionProperties

    def get_pull_commands(self) -> list[str]:
        """Return the commands to retrieve dependencies during the pull step."""
        return []

    @abc.abstractmethod
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""

    @abc.abstractmethod
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""

    @abc.abstractmethod
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return False

    @abc.abstractmethod
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""

    def set_action_properties(self, action_properties: ActionProperties) -> None:
        """Store a copy of the given action properties.

        :param action_properties: The properties to store.
        """
        self._action_properties = deepcopy(action_properties)


class JavaPlugin(Plugin):
    """A base class for java-related plugins.

    Provide common methods to deal with the java executable location and
    symlink creation.
    """

    def _get_java_post_build_commands(self) -> list[str]:
        """Get the bash commands to structure a Java build in the part's install dir.

        :return: The returned list contains the bash commands to do the following:

          - Create bin/ and jar/ directories in ${CRAFT_PART_INSTALL};
          - Find the ``java`` executable (provided by whatever jre the part used) and
            link it as ${CRAFT_PART_INSTALL}/bin/java;
          - Hardlink the .jar files generated in ${CRAFT_PART_BUILD} to
            ${CRAFT_PART_INSTALL}/jar.
        """
        # pylint: disable=line-too-long
        link_java = [
            '# Find the "java" executable and make a link to it in CRAFT_PART_INSTALL/bin/java',
            "mkdir -p ${CRAFT_PART_INSTALL}/bin",
            "java_bin=$(find ${CRAFT_PART_INSTALL} -name java -type f -executable)",
            "ln -s --relative $java_bin ${CRAFT_PART_INSTALL}/bin/java",
        ]

        link_jars = [
            "# Find all the generated jars and hardlink them inside CRAFT_PART_INSTALL/jar/",
            "mkdir -p ${CRAFT_PART_INSTALL}/jar",
            r'find ${CRAFT_PART_BUILD}/ -iname "*.jar" -exec ln {} ${CRAFT_PART_INSTALL}/jar \;',
        ]
        # pylint: enable=line-too-long

        return link_java + link_jars


class BasePythonPlugin(Plugin):
    """A base class for Python plugins.

    Provides common methods for dealing with Python items.
    """

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"findutils", "python3-dev", "python3-venv"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        python3_path = shutil.which("python3")
        if python3_path is None:
            raise errors.PluginEnvironmentValidationError(
                part_name=self._part_info._part_name,
                reason="cannot find a python3 executable on the system"
            )
        return {
            # Add PATH to the python interpreter we always intend to use with
            # this plugin. It can be user overridden, but that is an explicit
            # choice made by a user.
            "PATH": f"{self._part_info.part_install_dir}/bin:${{PATH}}",
            "PARTS_PYTHON_INTERPRETER": "python3",
            "PARTS_PYTHON_VENV_ARGS": "",
        }


    def _should_remove_symlinks(self) -> bool:
        """Configure executables symlink removal.

        This method can be overridden by application-specific subclasses to control
        whether symlinks in the virtual environment should be removed. Default is
        False.  If True, the venv-created symlinks to python* in bin/ will be
        removed and will not be recreated.
        """
        return False

    def _get_system_python_interpreter(self) -> str | None:
        """Obtain the path to the system-provided python interpreter.

        This method can be overridden by application-specific subclasses. It
        returns the path to the Python that bin/python3 should be symlinked to
        if Python is not part of the payload.
        """
        return '$(readlink -f "$(which "${PARTS_PYTHON_INTERPRETER}")")'

    def _get_script_interpreter(self) -> str:
        """Obtain the shebang line to use in Python scripts.

        This method can be overridden by application-specific subclasses. It
        returns the script interpreter to use in existing Python scripts.
        """
        return "#!/usr/bin/env ${PARTS_PYTHON_INTERPRETER}"
