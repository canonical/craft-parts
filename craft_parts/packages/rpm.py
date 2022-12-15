# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

"""Support for RPM files."""

import functools
import logging
import os
import pathlib
import subprocess
from pathlib import Path
from typing import List, Sequence, Set, Tuple

from craft_parts.utils import os_utils

from . import errors
from .base import BaseRepository, get_pkg_name_parts

logger = logging.getLogger(__name__)


class RPMRepository(BaseRepository):
    """Repository management for RPM packages."""

    @classmethod
    def configure(cls, application_package_name: str) -> None:
        """Set up apt options and directories."""
        print("============= REMOVED: AptCache.configure_apt(application_package_name)")

    @classmethod
    def get_package_libraries(cls, package_name: str) -> Set[str]:
        """Return a list of libraries in package_name."""
        print("============= REMOVED: _run_dpkg_query_list_files(package_name)")
        return []

    @classmethod
    def get_packages_for_source_type(cls, source_type):
        """Return a list of packages required to to work with source_type."""
        if source_type == "bzr":
            packages = {"bzr"}
        elif source_type == "git":
            packages = {"git"}
        elif source_type == "tar":
            packages = {"tar"}
        elif source_type in ["hg", "mercurial"]:
            packages = {"mercurial"}
        elif source_type == ["svn", "subversion"]:
            packages = {"subversion"}
        elif source_type == "rpm2cpio":
            # installed by default in CentOS systems
            packages = {}
        elif source_type == "7zip":
            packages = {"p7zip"}
        else:
            packages = set()

        return packages

    @classmethod
    @functools.lru_cache(maxsize=1)
    def refresh_packages_list(cls) -> None:
        """Refresh the list of packages available in the repository."""
        # Return early when testing.
        if os.getenv("CRAFT_PARTS_PACKAGE_REFRESH", "1") == "0":
            return

        try:
            cmd = ["yum", "update", "-y"]
            logger.debug("Executing: %s", cmd)
            process_run(cmd)
        except subprocess.CalledProcessError as call_error:
            raise errors.PackageListRefreshError(
                "failed to run yum update"
            ) from call_error

    @classmethod
    def _check_if_all_packages_installed(cls, package_names: List[str]) -> bool:
        """Check if all given packages are installed.

        Will check versions if using <pkg_name>=<pkg_version> syntax parsed by
        get_pkg_name_parts().  Used as an optimization to skip installation
        and cache refresh if dependencies are already satisfied.

        :return True if _all_ packages are installed (with correct versions).
        """
        # XXX need to do this
        return False

    @classmethod
    def _get_installed_package_versions(cls, package_names: Sequence[str]) -> List[str]:
        print("====================== USED??? 3")
        packages: List[str] = []

        with AptCache() as apt_cache:
            for package_name in package_names:
                package_version = apt_cache.get_installed_version(
                    package_name, resolve_virtual_packages=True
                )
                if package_version is None:
                    logger.debug("Expected package %s not installed", package_name)
                    continue
                logger.debug(
                    "Found installed version %s for package %s",
                    package_version,
                    package_name,
                )
                packages.append(f"{package_name}={package_version}")

        return packages

    @classmethod
    def _get_packages_marked_for_installation(
        cls, package_names: List[str]
    ) -> List[Tuple[str, str]]:
        print("====================== USED??? 4")
        with AptCache() as apt_cache:
            try:
                apt_cache.mark_packages(set(package_names))
            except errors.PackageNotFound as error:
                raise errors.BuildPackageNotFound(error.package_name)

            return apt_cache.get_packages_marked_for_installation()

    @classmethod
    def download_packages(cls, package_names: List[str]) -> None:
        """Download the specified packages to the local package cache area."""
        print("====================== USED??? 5")
        logger.info("Downloading packages: %s", " ".join(package_names))
        env = os.environ.copy()
        env.update(
            {
                "DEBIAN_FRONTEND": "noninteractive",
                "DEBCONF_NONINTERACTIVE_SEEN": "true",
                "DEBIAN_PRIORITY": "critical",
            }
        )

        apt_command = [
            "apt-get",
            "--no-install-recommends",
            "-y",
            "-oDpkg::Use-Pty=0",
            "--allow-downgrades",
            "--download-only",
            "install",
        ]

        try:
            process_run(apt_command + package_names, env=env)
        except subprocess.CalledProcessError as err:
            raise errors.PackagesDownloadError(packages=package_names) from err

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

        install_required = False
        package_names = sorted(package_names)

        logger.debug("Requested build-packages: %s", package_names)

        # Ensure we have an up-to-date cache first if we will have to
        # install anything.
        if not cls._check_if_all_packages_installed(package_names):
            install_required = True

        # # Collect the list of marked packages to later construct a manifest
        # marked_packages = cls._get_packages_marked_for_installation(package_names)
        # marked_package_names = [name for name, _ in sorted(marked_packages)]

        if not list_only:
            if refresh_package_cache and install_required:
                cls.refresh_packages_list()
            if install_required:
                cls._install_packages(package_names)
            else:
                logger.debug(
                    "Requested build-packages already installed: %s", package_names
                )

        # # This result is a best effort approach for deps and virtual packages
        # # as they are not part of the installation list.
        # return cls._get_installed_package_versions(marked_package_names)
        return []

    @classmethod
    def _install_packages(cls, package_names: List[str]) -> None:
        logger.debug("Installing packages: %s", " ".join(package_names))
        apt_command = ["yum", "install", "-y"]

        try:
            process_run(apt_command + package_names)
        except subprocess.CalledProcessError as err:
            raise errors.BuildPackagesNotInstalled(packages=package_names) from err

    @classmethod
    def is_package_installed(cls, package_name) -> bool:
        """Inform if a package is installed on the host system."""
        # XXX need to do this
        return False

    @classmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions."""
        # XXX need to do this
        return []


def get_cache_dirs(cache_dir: Path):
    """Return the paths to the stage and deb cache directories."""
    print("====================== USED??? A")
    stage_cache_dir = cache_dir / "stage-packages"
    deb_cache_dir = cache_dir / "download"

    return (stage_cache_dir, deb_cache_dir)


# XXX: this will be removed when user messages support is implemented.
def process_run(command: List[str], **kwargs) -> None:
    """Run a command and log its output."""
    # Pass logger so messages can be logged as originating from this package.
    os_utils.process_run(command, logger.debug, **kwargs)
