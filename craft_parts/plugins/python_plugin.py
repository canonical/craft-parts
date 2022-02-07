# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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

"""The python plugin."""

import shlex
from textwrap import dedent
from typing import Any, Dict, List, Set, cast

from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties


class PythonPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the python plugin."""

    python_requirements: List[str] = []
    python_constraints: List[str] = []
    python_packages: List[str] = ["pip", "setuptools", "wheel"]

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
            data, plugin_name="python", required=["source"]
        )
        return cls(**plugin_data)


class PythonPlugin(Plugin):
    """A plugin to build python parts.

    It can be used for python projects where you would want to do:

        - import python modules with a requirements.txt
        - build a python project that has a setup.py
        - install packages straight from pip

    This plugin uses the common plugin keywords as well as those for "sources".
    For more information check the 'plugins' topic for the former and the
    'sources' topic for the latter.

    Additionally, this plugin uses the following plugin-specific keywords:

        - ``python-requirements``
          (list of strings)
          List of paths to requirements files.

        - ``python-constraints``
          (list of strings)
          List of paths to constraint files.

        - ``python-packages``
          (list)
          A list of dependencies to get from PyPI. If needed, pip,
          setuptools and wheel can be upgraded here.

    This plugin also interprets these specific build-environment entries:

        - ``PARTS_PYTHON_INTERPRETER``
          (default: python3)
          The interpreter binary to search for in PATH.

        - ``PARTS_PYTHON_VENV_ARGS``
          Additional arguments for venv.

    By default this plugin uses python from the base. If a different
    interpreter is desired, it must be bundled (including venv) and must
    be in PATH.

    Use of python3-<python-package> in stage-packages will force the
    inclusion of the python interpreter.
    """

    properties_class = PythonPluginProperties

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        """Return a set of required packages to install in the build environment."""
        return {"findutils", "python3-dev", "python3-venv"}

    def get_build_environment(self) -> Dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {
            # Add PATH to the python interpreter we always intend to use with
            # this plugin. It can be user overridden, but that is an explicit
            # choice made by a user.
            "PATH": f"{self._part_info.part_install_dir}/bin:${{PATH}}",
            "PARTS_PYTHON_INTERPRETER": "python3",
            "PARTS_PYTHON_VENV_ARGS": "",
        }

    # pylint: disable=line-too-long

    def get_build_commands(self) -> List[str]:
        """Return a list of commands to run during the build step."""
        build_commands = [
            f'"${{PARTS_PYTHON_INTERPRETER}}" -m venv ${{PARTS_PYTHON_VENV_ARGS}} "{self._part_info.part_install_dir}"',
            f'PARTS_PYTHON_VENV_INTERP_PATH="{self._part_info.part_install_dir}/bin/${{PARTS_PYTHON_INTERPRETER}}"',
        ]

        options = cast(PythonPluginProperties, self._options)

        if options.python_constraints:
            constraints = " ".join(f"-c {c!r}" for c in options.python_constraints)
        else:
            constraints = ""

        if options.python_packages:
            python_packages = " ".join(
                [shlex.quote(pkg) for pkg in options.python_packages]
            )
            python_packages_cmd = f"pip install {constraints} -U {python_packages}"
            build_commands.append(python_packages_cmd)

        if options.python_requirements:
            requirements = " ".join(f"-r {r!r}" for r in options.python_requirements)
            requirements_cmd = f"pip install {constraints} -U {requirements}"
            build_commands.append(requirements_cmd)

        build_commands.append(f"[ -f setup.py ] && pip install {constraints} -U .")

        # Now fix shebangs.
        build_commands.append(
            dedent(
                f"""\
            find "{self._part_info.part_install_dir}" -type f -executable -print0 | xargs -0 \
                sed -i "1 s|^#\\!${{PARTS_PYTHON_VENV_INTERP_PATH}}.*$|#\\!/usr/bin/env ${{PARTS_PYTHON_INTERPRETER}}|"
            """
            )
        )

        # Lastly, fix the symlink to the "real" python3 interpreter.
        build_commands.append(
            dedent(
                f"""\
            determine_link_target() {{
                opts_state="$(set +o +x | grep xtrace)"
                interp_dir="$(dirname "${{PARTS_PYTHON_VENV_INTERP_PATH}}")"
                # Determine python based on PATH, then resolve it, e.g:
                # (1) <application venv dir>/bin/python3 -> /usr/bin/python3.8
                # (2) /usr/bin/python3 -> /usr/bin/python3.8
                # (3) /root/stage/python3 -> /root/stage/python3.8
                # (4) /root/parts/<part>/install/usr/bin/python3 -> /root/parts/<part>/install/usr/bin/python3.8
                python_path="$(which "${{PARTS_PYTHON_INTERPRETER}}")"
                python_path="$(readlink -e "${{python_path}}")"
                for dir in "{self._part_info.part_install_dir}" "{self._part_info.stage_dir}"; do
                    if  echo "${{python_path}}" | grep -q "${{dir}}"; then
                        python_path="$(realpath --strip --relative-to="${{interp_dir}}" \\
                                "${{python_path}}")"
                        break
                    fi
                done
                echo "${{python_path}}"
                eval "${{opts_state}}"
            }}

            python_path="$(determine_link_target)"
            ln -sf "${{python_path}}" "${{PARTS_PYTHON_VENV_INTERP_PATH}}"
            """
            )
        )

        return build_commands
