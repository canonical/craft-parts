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

"""Exceptions raised by the packages handling subsystem."""

from typing import Sequence

from craft_parts.errors import PartsError
from craft_parts.utils import formatting_utils


class PackagesError(PartsError):
    """Base class for package handler errors."""


class PackageBackendNotSupported(PartsError):
    """Requested package resolved not supported on this host."""

    def __init__(self, backend: str) -> None:
        self.backend = backend
        super().__init__(
            brief=f"Package backend {backend!r} is not supported on this environment.",
        )


class PackageNotFound(PackagesError):
    """Requested package doesn't exist in the remote repository.

    :param package_name: The name of the missing package.
    """

    def __init__(self, package_name: str):
        self.package_name = package_name
        brief = f"Package not found: {package_name}."

        super().__init__(brief=brief)


class PackagesNotFound(PackagesError):
    """Requested package doesn't exist in the remote repository.

    :param package_name: The names of the missing packages.
    """

    def __init__(self, packages: Sequence[str]):
        self.packages = packages
        missing_pkgs = formatting_utils.humanize_list(packages, "and")
        brief = f"Failed to find installation candidate for packages: {missing_pkgs}."
        resolution = (
            "Make sure the repository configuration and package names are correct."
        )

        super().__init__(brief=brief, resolution=resolution)


class PackageFetchError(PackagesError):
    """Failed to fetch package from remote repository.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to fetch package: {message}."

        super().__init__(brief=brief)


class PackageListRefreshError(PackagesError):
    """Failed to refresh the list of available packages.

    :param message: The error message.
    """

    def __init__(self, message: str):
        self.message = message
        brief = f"Failed to refresh package list: {message}."

        super().__init__(brief=brief)


class PackageBroken(PackagesError):
    """Package has unmet dependencies.

    :param package_name: The name of the package with unmet dependencies.
    :param deps: The list of unmet dependencies.
    """

    def __init__(self, package_name: str, *, deps: Sequence[str]):
        self.package_name = package_name
        self.deps = deps
        brief = f"Package {package_name!r} has unmet dependencies: {', '.join(deps)}."

        super().__init__(brief=brief)


class FileProviderNotFound(PackagesError):
    """A file is not provided by any package.

    :param file_path: The file path.
    """

    def __init__(self, *, file_path: str):
        self.file_path = file_path
        brief = f"{file_path} is not provided by any package."

        super().__init__(brief=brief)


class BuildPackageNotFound(PackagesError):
    """A package listed in 'build-packages' was not found.

    :param package: The name of the missing package.
    """

    def __init__(self, package):
        self.package = package
        brief = f"Cannot find package listed in 'build-packages': {package}"

        super().__init__(brief=brief)


class BuildPackagesNotInstalled(PackagesError):
    """Could not install all requested build packages.

    :param packages: The packages to install.
    """

    def __init__(self, *, packages: Sequence[str]) -> None:
        self.packages = packages
        brief = f"Cannot install all requested build packages: {', '.join(packages)}"

        super().__init__(brief=brief)


class PackagesDownloadError(PackagesError):
    """Failed to download packages from remote repository.

    :param packages: The packages to download.
    """

    def __init__(self, *, packages: Sequence[str]) -> None:
        self.packages = packages
        brief = f"Failed to download all requested packages: {', '.join(packages)}"
        resolution = (
            "Make sure the network configuration and package names are correct."
        )

        super().__init__(brief=brief, resolution=resolution)


class UnpackError(PackagesError):
    """Error unpacking stage package.

    :param package: The package that failed to unpack.
    """

    def __init__(self, package: str):
        self.package = package
        brief = f"Error unpacking {package!r}"

        super().__init__(brief=brief)


class SnapUnavailable(PackagesError):
    """Failed to install or refresh a snap.

    :param snap_name: The snap name.
    :param snap_channel: The snap channel.
    """

    def __init__(self, *, snap_name: str, snap_channel: str):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Failed to install or refresh snap {snap_name!r}."
        details = (
            f"{snap_name!r} does not exist or is not available on channel "
            f"{snap_channel!r}."
        )
        resolution = (
            f"Use `snap info {snap_name}` to get a list of channels the snap "
            "is available on."
        )

        super().__init__(brief=brief, details=details, resolution=resolution)


class SnapInstallError(PackagesError):
    """Failed to install a snap.

    :param snap_name: The snap name.
    :param snap_channel: The snap channel.
    """

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error installing snap {snap_name!r} from channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapDownloadError(PackagesError):
    """Failed to download a snap.

    :param snap_name: The snap name.
    :param snap_channel: The snap channel.
    """

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error downloading snap {snap_name!r} from channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapRefreshError(PackagesError):
    """Failed to refresh a snap.

    :param snap_name: The snap name.
    :param snap_channel: The snap channel.
    """

    def __init__(self, *, snap_name, snap_channel):
        self.snap_name = snap_name
        self.snap_channel = snap_channel
        brief = f"Error refreshing snap {snap_name!r} to channel {snap_channel!r}."

        super().__init__(brief=brief)


class SnapGetAssertionError(PackagesError):
    """Failed to retrieve snap assertion.

    :param assertion_params: The snap assertion parameters.
    """

    def __init__(self, *, assertion_params: Sequence[str]) -> None:
        self.assertion_params = assertion_params
        brief = f"Error retrieving assertion with parameters {assertion_params!r}"
        resolution = "Verify the assertion exists and try again."

        super().__init__(brief=brief, resolution=resolution)


class SnapdConnectionError(PackagesError):
    """Failed to connect to snapd.

    :param snap_name: The snap name.
    :param url: The failed connection URL.
    """

    def __init__(self, *, snap_name: str, url: str) -> None:
        self.snap_name = snap_name
        self.url = url
        brief = (
            f"Failed to get information for snap {snap_name!r}: could not connect "
            f"to {url!r}."
        )

        super().__init__(brief=brief)
