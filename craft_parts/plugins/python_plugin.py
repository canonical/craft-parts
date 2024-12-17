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

import csv
import email
from email.parser import HeaderParser
from overrides import override
from pathlib import Path
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
        # Could also add the pkginfo library for this

        venvdir = self._get_venv_directory()
        python_path = venvdir / "bin/python"
        python_version = python_path.resolve().name
        site_pkgs_dir = venvdir / "lib" / python_version / "site-packages"

        ret = {}
        for pkg_dir in site_pkgs_dir.iterdir():
            # We only care about the metadata dirs
            if not pkg_dir.name.endswith(".dist-info"):
                continue

            # Get package name and version from from METADATA file.
            # https://packaging.python.org/en/latest/specifications/core-metadata/
            parser = HeaderParser()
            with open(pkg_dir / "METADATA", "r") as f:
                pkg_metadata = parser.parse(f)
            pkg_name = pkg_metadata["Name"]
            pkg_version = pkg_metadata["Version"]

            # Read the RECORD file
            record_file = pkg_dir / "RECORD"
            with open(record_file, "r") as record_file_obj:
                csvreader = csv.reader(record_file_obj)

                # First column is files.  These are relative, resolve() to get
                # rid of all the ".." that leads up to the bin dir.
                pkg_files = {(site_pkgs_dir / f[0]).resolve() for f in csvreader}
                ret[Package(pkg_name, pkg_version)] = pkg_files
        return ret
