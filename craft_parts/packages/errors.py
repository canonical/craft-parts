# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Exceptions raised by the packages handling subsystem."""

from typing import Sequence

from craft_parts.errors import PartsError


class PackagesError(PartsError):
    """Base class for package handler errors."""


class PackageListRefreshError(PackagesError):
    """Failed to refresh the list of available packages."""

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to refresh package list: {message}."

        super().__init__(brief=brief)


class PackageFetchError(PackagesError):
    """Failed to fetch package from remote repository."""

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to fetch package: {message}."

        super().__init__(brief=brief)


class PackageNotFound(PackagesError):
    """Requested package doesn't exist in the remote repository."""

    def __init__(self, package_name: str):
        self.package_name = package_name
        brief = f"Package not found: {package_name}."

        super().__init__(brief=brief)


class PackageBroken(PackagesError):
    """Package has unmet dependencies."""

    def __init__(self, package_name: str, *, deps: Sequence[str]):
        self.package_name = package_name
        self.deps = deps
        brief = f"Package {package_name!r} has unmet dependencies: {', '.join(deps)}."

        super().__init__(brief=brief)


class FileProviderNotFound(PackagesError):
    """A file is not provided by any package."""

    def __init__(self, *, file_path: str):
        self.file_path = file_path
        brief = f"{file_path} is not provided by any package."

        super().__init__(brief=brief)


class BuildPackageNotFound(PackagesError):
    """A package listed in 'build-packages' was not found."""

    def __init__(self, package):
        self.package = package
        brief = f"Cannot find package listed in 'build-packages': {package}"

        super().__init__(brief=brief)


class BuildPackagesNotInstalled(PackagesError):
    """Could not install all requested build packages."""

    def __init__(self, *, packages: Sequence[str]) -> None:
        self.packages = packages
        brief = f"Cannot install all requested build packages: {', '.join(packages)}"

        super().__init__(brief=brief)


class UnpackError(PackagesError):
    """Error unpacking stage package."""

    def __init__(self, package: str):
        self.package = package
        brief = f"Error unpacking {package!r}"

        super().__init__(brief=brief)
