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

"""The python plugin."""

import shlex
from typing import Literal

import pydantic

from .base import BasePythonPlugin
from .properties import PluginProperties


class PythonPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the python plugin."""

    plugin: Literal["python"] = "python"

    python_requirements: list[str] = pydantic.Field(
        default=[],
        description="The paths to requirements files.",
    )
    """The paths to requirements files.

    Use this key when dependencies must be installed from one or more explicit
    requirements files, such as ``requirements.txt``. The plugin doesn't automatically
    select a requirements file from the source tree; each file must be listed here.

    A part doesn't need this key when its dependencies are already declared by the
    project metadata used during package installation. For example, when the source
    contains a ``setup.py`` or ``pyproject.toml`` file, the plugin installs the project
    and pip resolves the dependencies declared by the package itself. That metadata may
    also come from configuration files such as ``setup.cfg``.
    """

    python_constraints: list[str] = pydantic.Field(
        default=[],
        description="The paths to constraint files.",
    )
    """The paths to constraint files.
    """

    python_packages: list[str] = pydantic.Field(
        default=["pip", "setuptools", "wheel"],
        description="A dependencies to install from PyPI.",
    )
    """A dependencies to install from PyPI.

    If needed, ``pip``, ``setuptools`` and ``wheel`` can be upgraded here.
    """

    # part properties required by the plugin
    source: str


class PythonPlugin(BasePythonPlugin):
    """A plugin to build python parts."""

    properties_class = PythonPluginProperties
    _options: PythonPluginProperties

    def _get_package_install_commands(self) -> list[str]:
        commands: list[str] = []

        pip = self._get_pip()

        if self._options.python_constraints:
            constraints = " ".join(
                f"-c {c!r}" for c in self._options.python_constraints
            )
        else:
            constraints = ""

        if self._options.python_packages:
            python_packages = " ".join(
                [shlex.quote(pkg) for pkg in self._options.python_packages]
            )
            python_packages_cmd = f"{pip} install {constraints} -U {python_packages}"
            commands.append(python_packages_cmd)

        if self._options.python_requirements:
            requirements = " ".join(
                f"-r {r!r}" for r in self._options.python_requirements
            )
            requirements_cmd = f"{pip} install {constraints} -U {requirements}"
            commands.append(requirements_cmd)

        commands.append(
            f"[ -f setup.py ] || [ -f pyproject.toml ] && {pip} install {constraints} -U ."
        )

        return commands
