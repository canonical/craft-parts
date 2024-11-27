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

from email import policy
from email.parser import HeaderParser
import json
from pathlib import Path
import re
import shlex
from typing import Literal

from .base import BasePythonPlugin
from .properties import PluginProperties


_TEST_DIR_INSTALLABLE_CMD = "[ -f setup.py ] || [ -f pyproject.toml ]"
_PIP_SHOW_OUT_FILE = "pipshow.txt.eml"


class PythonPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the python plugin."""

    plugin: Literal["python"] = "python"

    python_requirements: list[str] = []
    python_constraints: list[str] = []
    python_packages: list[str] = ["pip", "setuptools", "wheel"]
    
    resolved_installed_packages: dict[str, Path] = {}

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


    def get_formatted_constraints(self) -> str:
        """Return a string ready to be passed as part of a pip command line.

        For instance: "-c constraints.txt -c constraints-dev.txt"
        """
        if not self.python_constraints:
            return ""
        return " ".join(
            f"-c {c!r}" for c in self.python_constraints
        )

    def get_formatted_requirements(self) -> str:
        """Return a string ready to be passed as part of a pip command line.

        For instance: "-r requirements.txt -r requirements-dev.txt"
        """
        return " ".join(
            f"-r {r!r}" for r in self.python_requirements
        )


    def get_formatted_packages(self) -> str:
        """Return a string ready to be passed as part of a pip command line.

        For instance: "'flask' 'requests'"
        """
        return " ".join(
            [shlex.quote(pkg) for pkg in self.python_packages]
        )


class PythonPlugin(BasePythonPlugin):
    """A plugin to build python parts."""

    properties_class = PythonPluginProperties
    _options: PythonPluginProperties

    def _get_package_install_commands(self) -> list[str]:
        install_commands = []

        pip = self._get_pip()
        constraints = self._options.get_formatted_constraints()

        if self._options.python_packages:
            python_packages = self._options.get_formatted_packages()
            python_packages_cmd = f"{pip} install {constraints} -U {python_packages}"
            install_commands.append(python_packages_cmd)

        if self._options.python_requirements:
            requirements = self._options.get_formatted_requirements()
            requirements_cmd = f"{pip} install {constraints} -U {requirements}"
            install_commands.append(requirements_cmd)

        install_commands.append(
            f"{_TEST_DIR_INSTALLABLE_CMD} && {pip} install {constraints} -U ."
        )

        return install_commands

    def get_post_install_file_list_commands(self) -> list[str]:
        # Make use of the JSON report pip can generate to figure out what dependencies resolved to in order to make up the whole package list.
        
        # The docs seem to indicate that passing "-r $file" and $package to pip install are mutually exclusive, as does the code above.  But adding them all together into one pip command seems to work.

        # If this approach doesn't pan out, we might try using something like pip-compile, or check out its code
        # https://github.com/jazzband/pip-tools

        resolve_deps_command = f"{self._get_pip()} install --dry-run --ignore-installed --quiet --report - "
        
        if self._options.python_packages:
            python_packages = self._options.get_formatted_packages()
            resolve_deps_command += python_packages + " "

        if self._options.python_requirements:
            requirements = self._options.get_formatted_requirements()
            resolve_deps_command += requirements + " "

        # Subshell inserts '.' into the list of pip things to get dependencies from
        resolve_deps_command += f"$({_TEST_DIR_INSTALLABLE_CMD} && echo .) "

        # Pipe the json to jq and extract the values we care about, package names
        resolve_deps_command += " | jq -r '.[\"install\"][][\"metadata\"][\"name\"]'"

        get_package_list_command = f"_PACKAGES_RESOLVED=\"$({resolve_deps_command})\""
        
        # Absurdly, 'pip show' outputs "RFC-compliant mail header format", according to the help output.  So parse that for the file list
        get_file_list_command = f"pip show -f $_PACKAGES_RESOLVED > $CRAFT_PART_BUILD/{_PIP_SHOW_OUT_FILE}"

        return [
            get_package_list_command,
            get_file_list_command,
        ]

    def read_file_list(self) -> dict[str, list[Path]]:
        linesep = policy.default.linesep
        msgsep = "---"
        parser = HeaderParser()

        with open(self._part_info.part_build_dir / _PIP_SHOW_OUT_FILE, "r") as f:
            all_packages_full_email = f.read().strip()

        # I figured there was a way to pass multiple emails as a single document using a separator, and if you ask pip show for information on multiple packages it will indeed separate each with "---" on its own line.  But I it doesn't seem that the python "email" package supports parsing this, and I couldn't find any info about this behavior in any RFC (though it's probably in one of them).
        all_packages_email_split = all_packages_full_email.split(f"{linesep}{msgsep}{linesep}")
       
        ret = {}
        #breakpoint()
        for package_raw_str in all_packages_email_split:
            if not package_raw_str:
                continue

            # Sometimes the output contains multiple newlines in a row, (like in the license text) which makes "email" think this is the end of the header, and everything following is message body.  Fix it with regex
            # TODO: compile regex
            normalized_package_raw_str = re.sub('\n+', '\n', package_raw_str.strip())

            # TODO: Actually it seems these license texts are actually a bigger problem than this regex can solve.  The not sure how to make the parser handle continuation lines in the license field.  Ignore for now

            package_message = parser.parsestr(normalized_package_raw_str)

            # TODO: Add some error handling to this - there could be all kinds of wacky inputs coming from these pip packages

            package_name = package_message["Name"]
            
            if not package_message['Files']:
                ret[package_name] = "<cannot parse>"
                continue

            package_files = [s.strip() for s in package_message["Files"].strip().splitlines()]
            ret[package_name] = package_files

        return ret

