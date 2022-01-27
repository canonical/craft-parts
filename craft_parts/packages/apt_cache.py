# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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

"""Manages the state of packages obtained using apt."""

from __future__ import annotations

import logging
import os
import re
import shutil
from contextlib import ContextDecorator
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import apt
import apt.cache
import apt.package
import apt.progress
import apt.progress.base
import apt_pkg

from craft_parts.utils import os_utils

from . import errors
from .base import get_pkg_name_parts

logger = logging.getLogger(__name__)


_HASHSUM_MISMATCH_PATTERN = re.compile(r"(E:Failed to fetch.+Hash Sum mismatch)+")


class LogProgress(apt.progress.base.AcquireProgress):
    """Internal Base class for text progress classes."""

    def __init__(self):
        self._id = 1

    def fail(self, item: apt_pkg.AcquireItemDesc) -> None:
        """Handle failed item."""
        apt.progress.base.AcquireProgress.fail(self, item)
        if item.owner.status == item.owner.STAT_DONE:
            logger.debug("Ign %s", item.description)
        else:
            logger.debug("Err %s", item.description)
            logger.debug("  %s", item.owner.error_text)

    def fetch(self, item: apt_pkg.AcquireItemDesc) -> None:
        """Handle item's data is fetch."""
        apt.progress.base.AcquireProgress.fetch(self, item)
        # It's complete already (e.g. Hit)
        if item.owner.complete:
            return
        item.owner.id = self._id
        self._id += 1
        line = f"Get: {item.owner.id} {item.description}"
        if item.owner.filesize:
            line += f" [{apt_pkg.size_to_str(item.owner.filesize)}B]"

        logger.debug(line)


class AptCache(ContextDecorator):
    """Transient cache for stage packages, or read-only for build packages."""

    def __init__(
        self,
        *,
        stage_cache: Optional[Path] = None,
        stage_cache_arch: Optional[str] = None,
    ) -> None:
        self.stage_cache = stage_cache
        self.stage_cache_arch = stage_cache_arch
        self.progress: Optional[LogProgress] = None

    # pylint: disable=attribute-defined-outside-init
    def __enter__(self) -> AptCache:
        if self.stage_cache is not None:
            self.progress = LogProgress()
            self._populate_stage_cache_dir()
            self.cache = apt.cache.Cache(rootdir=str(self.stage_cache), memonly=True)
        else:
            # Setting rootdir="/" is needed otherwise the previously set rootdir will
            # be used and _deb.get_installed_packages() will return an empty list.
            self.cache = apt.cache.Cache(rootdir="/")
        return self

    # pylint: enable=attribute-defined-outside-init

    def __exit__(self, *exc) -> None:
        self.cache.close()

    @classmethod
    def configure_apt(cls, application_package_name: str) -> None:
        """Set up apt options and directories."""
        # Do not install recommends.
        apt_pkg.config.set("Apt::Install-Recommends", "False")

        # Ensure repos are provided by trusted third-parties.
        apt_pkg.config.set("Acquire::AllowInsecureRepositories", "False")

        # Methods and solvers dir for when in the SNAP.
        snap_dir = os.getenv("SNAP")
        if (
            os_utils.is_snap(application_package_name)
            and snap_dir
            and os.path.exists(snap_dir)
        ):
            apt_dir = os.path.join(snap_dir, "usr", "lib", "apt")
            apt_pkg.config.set("Dir", apt_dir)
            # yes apt is broken like that we need to append os.path.sep
            methods_dir = os.path.join(apt_dir, "methods")
            apt_pkg.config.set("Dir::Bin::methods", methods_dir + os.path.sep)
            solvers_dir = os.path.join(apt_dir, "solvers")
            apt_pkg.config.set("Dir::Bin::solvers::", solvers_dir + os.path.sep)
            apt_key_path = os.path.join(snap_dir, "usr", "bin", "apt-key")
            apt_pkg.config.set("Dir::Bin::apt-key", apt_key_path)
            gpgv_path = os.path.join(snap_dir, "usr", "bin", "gpgv")
            apt_pkg.config.set("Apt::Key::gpgvcommand", gpgv_path)

        apt_pkg.config.set("Dir::Etc::Trusted", "/etc/apt/trusted.gpg")
        apt_pkg.config.set("Dir::Etc::TrustedParts", "/etc/apt/trusted.gpg.d/")
        apt_pkg.config.set("Dir::State", "/var/lib/apt")

        # Clear up apt's Post-Invoke-Success as we are not running
        # on the system.
        apt_pkg.config.clear("APT::Update::Post-Invoke-Success")

    def _populate_stage_cache_dir(self) -> None:
        """Create/refresh cache configuration.

        (1) Delete old-style symlink cache, if symlink.
        (2) Delete current-style (copied) tree.
        (3) Copy current host apt configuration.
        (4) Configure primary arch to target arch.
        (5) Install dpkg into cache directory to support multi-arch.
        """
        if self.stage_cache is None:
            return

        # Copy apt configuration from host.
        cache_etc_apt_path = Path(self.stage_cache, "etc", "apt")

        # Delete potentially outdated cache configuration.
        if cache_etc_apt_path.is_symlink():
            cache_etc_apt_path.unlink()
        elif cache_etc_apt_path.exists():
            shutil.rmtree(cache_etc_apt_path)

        # Copy current cache configuration.
        cache_etc_apt_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree("/etc/apt", cache_etc_apt_path)

        # Specify default arch (if specified).
        if self.stage_cache_arch is not None:
            arch_conf_path = cache_etc_apt_path / "apt.conf.d" / "00default-arch"
            arch_conf_path.write_text(f'APT::Architecture "{self.stage_cache_arch}";\n')

        # dpkg also needs to be in the rootdir in order to support multiarch
        # (apt calls dpkg --print-foreign-architectures).
        dpkg_path = shutil.which("dpkg")
        if dpkg_path:
            # Symlink it into place
            destination = Path(self.stage_cache, dpkg_path[1:])
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(dpkg_path, destination)
        else:
            logger.warning("Cannot find 'dpkg' command needed to support multiarch")

    def _autokeep_packages(self) -> None:
        # If the package has been installed automatically as a dependency
        # of another package, and if no packages depend on it anymore,
        # the package is no longer required.
        for package in self.cache.get_changes():
            if package.is_auto_removable:
                package.mark_keep()

    def is_package_valid(self, package_name: str) -> bool:
        """Verify whether there is a valid package with the given name.

        :param package_name: The name of the package to verify.

        :return: Whether a package with the given name is valid.
        """
        return package_name in self.cache or self.cache.is_virtual_package(package_name)

    def get_installed_version(
        self, package_name: str, *, resolve_virtual_packages: bool = False
    ) -> Optional[str]:
        """Obtain the version of the package currently installed on the system.

        :param package_name: The package installed on the system.
        :param resolve_virtual_packages: If the package is virtual, pick a non-virtual
            package that satisfies this virtual package name.

        :return: The installed package version.
        """
        if resolve_virtual_packages and self.cache.is_virtual_package(package_name):
            logger.warning(
                "%s is a virtual package, use non-virtual packages for "
                "deterministic results.",
                package_name,
            )
            # Recurse until a "real" package is found.
            return self.get_installed_version(
                self.cache.get_providing_packages(package_name)[0].name,
                resolve_virtual_packages=resolve_virtual_packages,
            )

        if package_name in self.cache:
            installed = self.cache[package_name].installed
            if installed is not None:
                return installed.version
        return None

    def fetch_archives(self, download_path: Path) -> List[Tuple[str, str, Path]]:
        """Retrieve packages marked to be fetched.

        :param download_path: The directory to download files to.

        :return: A list of (<package-name>, <package-version>, <dl-path>) tuples.
        """
        downloaded = []
        for package in self.cache.get_changes():
            if package.candidate is None:
                continue

            try:
                dl_path = package.candidate.fetch_binary(
                    str(download_path), progress=self.progress
                )
            except apt.package.FetchError as err:
                raise errors.PackageFetchError(str(err))

            if package.candidate is None:
                raise errors.PackageNotFound(package.name)

            downloaded.append((package.name, package.candidate.version, Path(dl_path)))
        return downloaded

    def get_installed_packages(self) -> Dict[str, str]:
        """Obtain a list of all packages and versions installed on the system.

        :return: A dictionary of files and installed versions.
        """
        installed: Dict[str, str] = {}
        for package in self.cache:
            if package.installed is not None:
                installed[package.name] = str(package.installed.version)

        return installed

    def get_packages_marked_for_installation(self) -> List[Tuple[str, str]]:
        """Obtain a list of packages and versions to be installed on the system.

        :return: A list of (<package-name>, <package-version>) tuples.
        """
        changed_pkgs = self.cache.get_changes()
        marked_install_pkgs = [p for p in changed_pkgs if p.marked_install]
        missing_installation_candidate = [
            p.name for p in marked_install_pkgs if p.candidate is None
        ]

        if missing_installation_candidate:
            raise errors.PackagesNotFound(missing_installation_candidate)

        return [
            (p.name, p.candidate.version) for p in marked_install_pkgs  # type: ignore
        ]

    def mark_packages(self, package_names: Set[str]) -> None:
        """Mark the given package names to be fetched from the repository.

        :param package_names: The set of package names to be marked.
        """
        for name in package_names:
            if name.endswith(":any"):
                name = name[:-4]

            if self.cache.is_virtual_package(name):
                name = self.cache.get_providing_packages(name)[0].name

            logger.debug("Marking %s (and its dependencies) to be fetched", name)

            name_arch, version = get_pkg_name_parts(name)
            if name_arch not in self.cache:
                raise errors.PackageNotFound(name_arch)

            package = self.cache[name_arch]
            if version is not None:
                _set_pkg_version(package, version)

            logger.debug("package: %s", package)

            # Disable automatic resolving of broken packages here
            # because if that fails it raises a SystemError and the
            # API doesn't expose enough information about the problem.
            # Instead we let apt-get show a verbose error message later.
            # Also, make sure this package is marked as auto-installed,
            # which will propagate to its dependencies.
            package.mark_install(auto_fix=False, from_user=False)

            # Now mark this package as NOT automatically installed, which
            # will leave its dependencies marked as auto-installed, which
            # allows us to clean them up if necessary.
            package.mark_auto(False)

            _verify_marked_install(package)

    def unmark_packages(self, unmark_names: Set[str]) -> None:
        """Unmark packages and dependencies that are no longer required.

        :param unmark_names: The names of the packages to unmark.
        """
        skipped_essential = set()
        skipped_filtered = set()

        for package in self.cache.get_changes():
            if package.candidate is None:
                raise errors.PackageNotFound(package.name)

            if package.candidate.priority == "essential":
                # Filter 'essential' packages.
                skipped_essential.add(package.name)
                package.mark_keep()
                continue

            if package.name in unmark_names:
                # Filter packages from given list.
                skipped_filtered.add(package.name)
                package.mark_keep()
                continue

        if skipped_essential:
            logger.debug(
                "Skipping priority essential packages: %s",
                sorted(skipped_essential),
            )

        if skipped_filtered:
            logger.debug(
                "Skipping filtered manifest packages: %s",
                sorted(skipped_filtered),
            )

        # Unmark dependencies that are no longer required.
        self._autokeep_packages()


def _verify_marked_install(package: apt.package.Package):
    if package.installed or package.marked_install:
        return

    if package.candidate is None:
        raise errors.PackageNotFound(package.name)

    broken_deps: List[str] = []
    for package_dependencies in package.candidate.dependencies:
        for dep in package_dependencies:
            if not dep.target_versions:
                broken_deps.append(dep.name)
    raise errors.PackageBroken(package.name, deps=broken_deps)


def _set_pkg_version(package: apt.package.Package, version: str) -> None:
    """Set candidate version to a specific version if available."""
    if version in package.versions:
        pkg_version = package.versions.get(version)
        if pkg_version:
            package.candidate = pkg_version
    else:
        raise errors.PackageNotFound(f"{package.name}={version}")
