# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2025 Canonical Ltd.
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
import pathlib
import textwrap
from copy import deepcopy
from typing import TYPE_CHECKING

from overrides import override

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
        """Return a set of required packages to install in the build environment.

        Child classes that need to override this should extend the returned set.
        """
        return {"findutils", "python3-dev", "python3-venv"}

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step.

        Child classes that need to override this should extend the dictionary returned
        by this class.
        """
        return {
            # Add PATH to the python interpreter we always intend to use with
            # this plugin. It can be user overridden, but that is an explicit
            # choice made by a user.
            "PATH": f"{self._part_info.part_install_dir}/bin:${{PATH}}",
            "PARTS_PYTHON_INTERPRETER": "python3",
            "PARTS_PYTHON_VENV_ARGS": "",
        }

    def _get_venv_directory(self) -> pathlib.Path:
        """Get the directory into which the virtualenv should be placed.

        This method can be overridden by application-specific subclasses to control
        the location of the virtual environment if it should be a subdirectory of
        the install dir.
        """
        return self._part_info.part_install_dir

    def _get_create_venv_commands(self) -> list[str]:
        """Get the commands for setting up the virtual environment."""
        venv_dir = self._get_venv_directory()
        return [
            f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{venv_dir}"',
            f'PARTS_PYTHON_VENV_INTERP_PATH="{venv_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        ]

    def _get_find_python_interpreter_commands(self) -> list[str]:
        """Get the commands that find a staged Python interpreter.

        These commands should, in bash, have a side-effect of creating a variable
        called ``symlink_target`` containing the path to the relevant Python payload.
        """
        python_interpreter = self._get_system_python_interpreter() or ""
        return [
            textwrap.dedent(
                f"""\
            # look for a provisioned python interpreter
            opts_state="$(set +o|grep errexit)"
            set +e
            install_dir="{self._part_info.part_install_dir}/usr/bin"
            stage_dir="{self._part_info.stage_dir}/usr/bin"

            # look for the right Python version - if the venv was created with python3.10,
            # look for python3.10
            basename=$(basename $(readlink -f ${{PARTS_PYTHON_VENV_INTERP_PATH}}))
            echo Looking for a Python interpreter called \\"${{basename}}\\" in the payload...
            payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "${{basename}}" -print -quit 2>/dev/null || true)

            if [ -n "$payload_python" ]; then
                # We found a provisioned interpreter, use it.
                echo Found interpreter in payload: \\"${{payload_python}}\\"
                installed_python="${{payload_python##{self._part_info.part_install_dir}}}"
                if [ "$installed_python" = "$payload_python" ]; then
                    # Found a staged interpreter.
                    symlink_target="..${{payload_python##{self._part_info.stage_dir}}}"
                else
                    # The interpreter was installed but not staged yet.
                    symlink_target="..$installed_python"
                fi
            else
                # Otherwise use what _get_system_python_interpreter() told us.
                echo "Python interpreter not found in payload." >&2
                symlink_target="{python_interpreter}"
            fi

            if [ -z "$symlink_target" ]; then
                echo "No suitable Python interpreter found, giving up." >&2
                exit 1
            fi

            eval "${{opts_state}}"
            """
            )
        ]

    def _get_rewrite_shebangs_commands(self) -> list[str]:
        """Get the commands used to rewrite shebangs in the install dir.

        This can be overridden by application-specific subclasses to control how Python
        shebangs in the final environment should be handled.
        """
        script_interpreter = self._get_script_interpreter()
        find_cmd = (
            f'find "{self._part_info.part_install_dir}" -type f -executable -print0'
        )
        xargs_cmd = "xargs --no-run-if-empty -0"
        sed_cmd = f'sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|{script_interpreter}|"'
        return [
            textwrap.dedent(
                f"""\
                {find_cmd} | {xargs_cmd} \\
                    {sed_cmd}
                """
            )
        ]

    def _get_handle_symlinks_commands(self) -> list[str]:
        """Get commands for handling Python symlinks."""
        if self._should_remove_symlinks():
            venv_dir = self._get_venv_directory()
            return [
                f"echo Removing python symlinks in {venv_dir}/bin",
                f'rm "{venv_dir}"/bin/python*',
            ]
        return ['ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"']

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

    def _get_pip(self) -> str:
        """Get the pip command to use."""
        return f"{self._get_venv_directory()}/bin/pip"

    @abc.abstractmethod
    def _get_package_install_commands(self) -> list[str]:
        """Get the commands for installing the given package in the Python virtualenv.

        A specific Python build system plugin should override this method to provide
        the necessary commands.
        """

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        return [
            *self._get_create_venv_commands(),
            *self._get_package_install_commands(),
            *self._get_rewrite_shebangs_commands(),
            *self._get_find_python_interpreter_commands(),
            *self._get_handle_symlinks_commands(),
        ]
