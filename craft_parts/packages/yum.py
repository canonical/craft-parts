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

"""Support for files installed/updated through YUM."""

import logging
import subprocess
from typing import List, Set

from craft_parts.utils import os_utils

from . import errors
from .base import BaseRepository

logger = logging.getLogger(__name__)


class YUMRepository(BaseRepository):
    """Repository management using YUM."""

    @classmethod
    def configure(cls, application_package_name: str) -> None:
        """Set up yum options and directories.

        XXX: method left out of YUMRepository's MVP; it should be implemented
        in the future to allow configuring the yum system.
        """
        logger.debug(
            "Called not implemented method 'YUMRepository.configure' with name %r",
            application_package_name,
        )

    @classmethod
    def get_package_libraries(
        cls, package_name: str
    ) -> Set[str]:  # pylint: disable=unused-argument
        """Return a list of libraries in package_name.

        XXX: method left out of YUMRepository's MVP; cannot return a sane default so
        raising an error to ensure it's not used.
        """
        raise NotImplementedError("Functionality not yet provided by YUMRepository.")

    @classmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to work with source_type."""
        if source_type == "bzr":
            packages = {"bzr"}
        elif source_type == "git":
            packages = {"git"}
        elif source_type == "tar":
            packages = {"tar"}
        elif source_type in ["hg", "mercurial"]:
            packages = {"mercurial"}
        elif source_type in ["svn", "subversion"]:
            packages = {"subversion"}
        elif source_type in ["rpm2cpio", "rpm"]:
            # installed by default in CentOS systems by the rpm package
            packages = set()
        elif source_type == "7zip":
            packages = {"p7zip"}
        elif source_type == "deb":
            raise NotImplementedError("Deb files not yet supported on this base.")
        else:
            packages = set()

        return packages

    @classmethod
    def refresh_packages_list(cls) -> None:
        """Refresh the list of packages available in the repository.

        This is a NOOP in YUM based systems because `yum install` updates the cache
        itself, no separate previous action is needed.
        """

    @classmethod
    def _check_if_all_packages_installed(cls, package_names: List[str]) -> bool:
        """Check if all given packages are installed.

        Will check versions if using <pkg_name>=<pkg_version> syntax parsed by
        get_pkg_name_parts().  Used as an optimization to skip installation
        and cache refresh if dependencies are already satisfied.

        :return: True if _all_ packages are installed (with correct versions).

        XXX: method left out of YUMRepository's MVP; returning False would lead to
        an inefficiency, this should be implemented in the future.
        """
        logger.debug(
            "Called not implemented method "
            "'YUMRepository._check_if_all_packages_installed' "
            "with names %s",
            package_names,
        )
        return False

    @classmethod
    def download_packages(cls, package_names: List[str]) -> None:
        """Download the specified packages to the local package cache area.

        XXX: method left out of YUMRepository's MVP; nothing will be
        downloaded, so raise an error to ensure it's not used.
        """
        raise NotImplementedError("Functionality not yet provided by YUMRepository.")

    @classmethod
    def install_packages(
        cls,
        package_names: List[str],
        *,
        list_only: bool = False,
        refresh_package_cache: bool = True,
    ) -> List[str]:
        """Install packages on the host system."""
        if not package_names:
            return []

        package_names = sorted(package_names)
        logger.debug("Requested packages: %s", package_names)

        install_required = False
        if not cls._check_if_all_packages_installed(package_names):
            install_required = True

        if not list_only:
            if refresh_package_cache and install_required:
                cls.refresh_packages_list()
            if install_required:
                cls._install_packages(package_names)
            else:
                logger.debug("Requested packages already installed: %s", package_names)

        # XXX Facundo 2023-02-07: the information returned by this method is not used
        # anywhere, so we should clean it up and just return None (here, and in the
        # Ubuntu reposity too, where a further cleaning should be done) -- related
        # to this, `list_only` should go away.
        return []

    @classmethod
    def _install_packages(cls, package_names: List[str]) -> None:
        """Really install the packages."""
        logger.debug("Installing packages: %s", " ".join(package_names))
        yum_command = ["yum", "install", "-y"]
        try:
            process_run(yum_command + package_names)
        except subprocess.CalledProcessError as err:
            raise errors.BuildPackagesNotInstalled(packages=package_names) from err

    @classmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Inform if a package is installed on the host system.

        XXX: method left out of YUMRepository's MVP; returning False would lead to
        an inefficiency, this should be implemented in the future.
        """
        logger.debug(
            "Called not implemented method 'YUMRepository.is_package_installed' "
            "with name %r",
            package_name,
        )
        return False

    @classmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions.

        XXX: method left out of YUMRepository's MVP; returning an empty list
        would lead to an inefficiency, this should be implemented in the future.
        """
        logger.debug(
            "Called not implemented method 'YUMRepository.get_installed_packages'"
        )
        return []


def process_run(command: List[str]) -> None:
    """Run a command and log its output."""
    # Pass logger so messages can be logged as originating from this package.
    os_utils.process_run(command, logger.debug)
