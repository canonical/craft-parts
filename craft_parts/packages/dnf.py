# Copyright 2023 Canonical Ltd.
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

"""Support for files installed/updated through DNF."""

# pylint:disable=duplicate-code

import logging
import subprocess
from typing import List, Set

from craft_parts.utils import os_utils

from . import errors
from .yum import YUMRepository

logger = logging.getLogger(__name__)


class DNFRepository(YUMRepository):
    """Repository management using DNF."""

    @classmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to work with source_type."""
        if source_type == "bzr":
            raise NotImplementedError(
                "bzr version control system is not yet supported on this base."
            )
        if source_type == "deb":
            raise NotImplementedError("Deb files not yet supported on this base.")

        if source_type == "git":
            packages = {"git"}
        elif source_type == "tar":
            packages = {"tar"}
        elif source_type in ["hg", "mercurial"]:
            packages = {"mercurial"}
        elif source_type in ["svn", "subversion"]:
            packages = {"subversion"}
        elif source_type in ["rpm2cpio", "rpm"]:
            packages = set()
        elif source_type == "7zip":
            packages = {"p7zip"}
        else:
            packages = set()

        return packages

    @classmethod
    def _install_packages(cls, package_names: List[str]) -> None:
        """Really install the packages."""
        logger.debug("Installing packages: %s", " ".join(package_names))
        dnf_command = ["dnf", "install", "-y"]
        try:
            process_run(dnf_command + package_names)
        except subprocess.CalledProcessError as err:
            raise errors.BuildPackagesNotInstalled(packages=package_names) from err


def process_run(command: List[str]) -> None:
    """Run a command and log its output."""
    # Pass logger so messages can be logged as originating from this package.
    os_utils.process_run(command, logger.debug)
