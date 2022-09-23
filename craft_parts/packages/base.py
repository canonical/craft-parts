# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Definition and helpers for the repository base class."""

import abc
import contextlib
import logging
import os
from pathlib import Path
from typing import List, Optional, Set, Tuple, Type

from craft_parts import xattrs

logger = logging.getLogger(__name__)


class BaseRepository(abc.ABC):
    """Base implementation for a platform specific repository handler."""

    @classmethod
    @abc.abstractmethod
    def configure(cls, application_package_name: str) -> None:
        """Set up the repository."""

    @classmethod
    @abc.abstractmethod
    def get_package_libraries(cls, package_name: str) -> Set[str]:
        """Return a list of libraries in package_name.

        Given the contents of package_name, return the subset of what are
        considered libraries from those contents, be it static or shared.

        :param package_name: The package name to get library contents from.
        :return: A list of libraries that package_name provides, with paths.
        """

    @classmethod
    @abc.abstractmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to to work with source_type.

        :param source_type: A source type to handle.

        :return: A set of packages that need to be installed on the host.
        """

    @classmethod
    @abc.abstractmethod
    def refresh_packages_list(cls) -> None:
        """Refresh the list of packages available in the repository.

        If refreshing is not possible :class:`PackageListRefreshError`
        should be raised.
        """

    @classmethod
    @abc.abstractmethod
    def download_packages(cls, package_names: List[str]) -> None:
        """Download the specified packages to the local package cache.

        :param package_names: A list with the names of the packages to download.
        """

    # XXX: list-only functionality can be a method called by install_build_packages

    @classmethod
    @abc.abstractmethod
    def install_packages(
        cls,
        package_names: List[str],
        *,
        list_only: bool = False,
        refresh_package_cache: bool = True,
    ) -> List[str]:
        """Install packages on the host system.

        This method needs to be implemented by using the appropriate mechanism
        to install packages on the system. If possible they should be marked
        as automatically installed to allow for easy removal. The method
        should return a list of the actually installed packages in the form
        "package=version".

        If one of the packages cannot be found :class:`BuildPackageNotFound`
        should be raised. If dependencies for a package cannot be resolved
        :class:`PackageBroken` should be raised. If installing a package on the
        host failed :class:`BuildPackagesNotInstalled` should be raised.

        :param package_names: A list of package names to install.
        :param list_only: Only list the packages that would be installed.
        :param refresh_package_cache: Refresh the cache before installing.

        :return: A list with the packages installed and their versions.
        """

    @classmethod
    @abc.abstractmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Inform if a package is installed on the host system.

        :param package_name: The package name to query.

        :return: Whether the package is installed.
        """

    @classmethod
    @abc.abstractmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions.

        :return: A list of installed packages in the form package=version.
        """

    @classmethod
    @abc.abstractmethod
    def fetch_stage_packages(
        cls,
        *,
        cache_dir: Path,
        package_names: List[str],
        stage_packages_path: Path,
        base: str,
        arch: str,
        list_only: bool = False,
    ) -> List[str]:
        """Fetch stage packages to stage_packages_path.

        :param application_name: A unique identifier for the application
            using Craft Parts.
        :param package_names: A list with the names of the packages to fetch.
        :stage_packages_path: The path stage packages will be fetched to.
        :param base: The base this project will run on.
        :param arch: The architecture of the packages to fetch.
        :param list_only: Whether to obtain a list of packages to be fetched
            instead of actually fetching the packages.

        :return: The list of all packages to be fetched, including dependencies.
        """

    @classmethod
    @abc.abstractmethod
    def unpack_stage_packages(
        cls,
        *,
        stage_packages_path: Path,
        install_path: Path,
        stage_packages: Optional[List[str]] = None,
    ) -> None:
        """Unpack stage packages.

        :param stage_packages_path: The path to the directory containing the
            stage packages to unpack.
        :param install_path: The path stage packages will be unpacked to.
        :param stage_packages: An optional list of the packages that were previously
            pulled.
        """


RepositoryType = Type[BaseRepository]


class DummyRepository(BaseRepository):
    """A dummy repository."""

    @classmethod
    def configure(cls, application_package_name: str) -> None:
        """Set up the repository."""

    @classmethod
    def get_package_libraries(cls, package_name: str) -> Set[str]:
        """Return a list of libraries in package_name."""
        return set()

    @classmethod
    def get_packages_for_source_type(cls, source_type: str) -> Set[str]:
        """Return a list of packages required to to work with source_type."""
        return set()

    @classmethod
    def refresh_packages_list(cls) -> None:
        """Refresh the build packages cache."""

    @classmethod
    def download_packages(cls, package_names: List[str]) -> None:
        """Download the specified packages to the local package cache."""

    @classmethod
    def install_packages(
        cls,
        package_names: List[str],
        *,
        list_only: bool = False,  # pylint: disable=unused-argument
        refresh_package_cache: bool = True,  # pylint: disable=unused-argument
    ) -> List[str]:
        """Install packages on the host system."""
        return []

    @classmethod
    def is_package_installed(cls, package_name: str) -> bool:
        """Inform if a packahe is installed on the host system."""
        return False

    @classmethod
    def get_installed_packages(cls) -> List[str]:
        """Obtain a list of the installed packages and their versions."""
        return []

    @classmethod
    def fetch_stage_packages(
        cls,
        **kwargs,  # pylint: disable=unused-argument
    ) -> List[str]:
        """Fetch stage packages to stage_packages_path."""
        return []

    @classmethod
    def unpack_stage_packages(
        cls,
        *,
        stage_packages_path: Path,
        install_path: Path,
        stage_packages: Optional[List[str]] = None,
    ) -> None:
        """Unpack stage packages to install_path."""


def get_pkg_name_parts(pkg_name: str) -> Tuple[str, Optional[str]]:
    """Break package name into base parts."""
    name = pkg_name
    version = None
    with contextlib.suppress(ValueError):
        name, version = pkg_name.split("=")

    return name, version


def mark_origin_stage_package(sources_dir: str, stage_package: str) -> Set[str]:
    """Mark all files in sources_dir as coming from stage_package."""
    file_list = set()
    for (root, _, files) in os.walk(sources_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)

            # Mark source.
            xattrs.write_origin_stage_package(file_path, stage_package)

            file_path = os.path.relpath(root, sources_dir)
            file_list.add(file_path)

    return file_list
