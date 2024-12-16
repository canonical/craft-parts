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

from .base import BasePythonPlugin, Package, PackageFiles
from .properties import PluginProperties


class PythonPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the python plugin."""

    plugin: Literal["python"] = "python"

    python_requirements: list[str] = []
    python_constraints: list[str] = []
    python_packages: list[str] = ["pip", "setuptools", "wheel"]

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class PythonPlugin(BasePythonPlugin):
    """A plugin to build python parts."""

    properties_class = PythonPluginProperties
    _options: PythonPluginProperties

    def _get_package_install_commands(self) -> list[str]:
        commands = []

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

    
    @override
    def get_files(self) -> PackageFiles:
        # https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        # Read the RECORD files

        venvdir = self._get_venv_directory()
        python_path = venvdir / "bin/python"
        python_version = python_path.resolve().name

        site_pkgs_dir = venvdir / "lib" / python_version / "site-packages"

        # Could also add the pkginfo library and skip a lot of the below

        ret = {}
        for pkg_dir in site_pkgs_dir.iterdir():
            # We only care about the metadata dirs
            if not pkg_dir.name.endswith(".dist-info"):
                continue

            # Get package name and version from filename - could also parse it from METADATA
            # I assume there must be at least one character for version, not sure what else it could look like though.  I've seen:
            # - 0.0.0
            # - 0.0
            # TODO: look this up
            pkg_name_match = re.match(r"^(.*)-[0-9.]+\.dist-info$", pkg_dir.name)
            if not pkg_name_match:
                raise Exception(f"Unexpectedly formatted dist-info dir: {pkg_dir.name!r}")
            pkg_name = pkg_name_match[1]

            record_file = pkg_dir / "RECORD"
            with open(record_file, "r") as f:
                csvreader = csv.reader(f)

                # First row is files
                # TODO: Remove all files listed under the dist-info dir?
                pkg_files = [Path(f[0]) for f in csvreader]
                ret[pkg_name] = pkg_files
        return ret
