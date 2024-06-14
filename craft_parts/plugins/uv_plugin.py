# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

"""A Python plugin that uses uv rather than pip."""

import shlex
from textwrap import dedent
from typing import Any, Dict, List, Optional, Set, cast

from overrides import override

from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties
from .python_plugin import PythonPlugin, PythonPluginProperties


class UvPluginProperties(PluginProperties):
    """The part properties used by the python plugin."""

    uv_requirements: List[str] = []
    uv_constraints: List[str] = []
    uv_packages: List[str] = ["pip", "setuptools", "wheel"]

    # part properties required by the plugin
    source: str

    @classmethod
    @override
    def unmarshal(cls, data: Dict[str, Any]) -> "UvPluginProperties":
        """Populate make properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="uv", required=["source"]
        )
        return cls(**plugin_data)


class UvPlugin(PythonPlugin):
    """A plugin to build python parts."""

    properties_class = UvPluginProperties

    @override
    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            # Add PATH to the python interpreter we always intend to use with
            # this plugin. It can be user overridden, but that is an explicit
            # choice made by a user.
            "PATH": f"{self._part_info.part_install_dir}/bin:${{PATH}}",
            "PARTS_PYTHON_INTERPRETER": "python",
            "PARTS_PYTHON_VENV_ARGS": "",
        }

    @override
    def get_pull_commands(self) -> List[str]:
        """Return a list of commands to run during the pull step."""
        return [
            "curl -LsSf https://astral.sh/uv/install.sh | sh"
        ]

    @override
    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        uv = f'"${{HOME}}"/.cargo/bin/uv'
        build_commands = [
            f'{uv} venv ${{PARTS_PYTHON_VENV_ARGS}} "{self._part_info.part_install_dir}"',
            f'PARTS_PYTHON_VENV_INTERP_PATH="{self._part_info.part_install_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
            f"VIRTUAL_ENV={self._part_info.part_install_dir}",
        ]

        options = cast(UvPluginProperties, self._options)

        pip = f"{uv} pip"

        if options.uv_constraints:
            constraints = " ".join(f"-c {c!r}" for c in options.uv_constraints)
        else:
            constraints = ""

        if options.uv_packages:
            python_packages = " ".join(
                [shlex.quote(pkg) for pkg in options.uv_packages]
            )
            python_packages_cmd = f"{pip} install {constraints} -U {python_packages}"
            build_commands.append(python_packages_cmd)

        if options.uv_requirements:
            requirements = " ".join(f"-r {r!r}" for r in options.uv_requirements)
            requirements_cmd = f"{pip} install {constraints} -U {requirements}"
            build_commands.append(requirements_cmd)

        build_commands.append(
            f"[ -f setup.py ] || [ -f pyproject.toml ] && {pip} install {constraints} -U ."
        )

        # Now fix shebangs.
        script_interpreter = self._get_script_interpreter()
        build_commands.append(
            dedent(
                f"""\
                find "{self._part_info.part_install_dir}" -type f -executable -print0 | xargs -0 \\
                    sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|{script_interpreter}|"
                """
            )
        )
        # Find the "real" python3 interpreter.
        python_interpreter = self._get_system_python_interpreter() or ""
        build_commands.append(
            dedent(
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
                payload_python=$(find "$install_dir" "$stage_dir" -type f -executable -name "${{basename}}" -print -quit 2>/dev/null)

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
                    echo "Python interpreter not found in payload."
                    symlink_target="{python_interpreter}"
                fi

                if [ -z "$symlink_target" ]; then
                    echo "No suitable Python interpreter found, giving up."
                    exit 1
                fi

                eval "${{opts_state}}"
                """
            )
        )

        # Handle the venv symlink (either remove it or set the final correct target)
        if self._should_remove_symlinks():
            build_commands.append(
                dedent(
                    f"""\
                    echo Removing python symlinks in {self._part_info.part_install_dir}/bin
                    rm "{self._part_info.part_install_dir}"/bin/python*
                    """
                )
            )
        else:
            build_commands.append(
                dedent(
                    """\
                    ln -sf "${symlink_target}" "${PARTS_PYTHON_VENV_INTERP_PATH}"
                    """
                )
            )

        return build_commands
