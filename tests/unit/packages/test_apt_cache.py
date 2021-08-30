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

import os
from pathlib import Path
from typing import cast
from unittest.mock import call

import apt.package
import pytest

from craft_parts.packages import apt_cache, errors
from craft_parts.packages.apt_cache import AptCache

# xpylint: disable=too-few-public-methods


class TestAptStageCache:
    """Make sure the stage cache is working correctly.

    This are expensive tests, but is much more valuable than using mocks.
    When adding tests, consider adding it to test_stage_packages(), or
    create mocks.
    """

    def test_stage_packages(self, tmpdir):
        fetch_dir_path = Path(tmpdir, "debs")
        fetch_dir_path.mkdir(exist_ok=True, parents=True)
        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)

        AptCache.configure_apt("test_stage_packages")
        with AptCache(stage_cache=stage_cache) as apt_cache:
            package_names = {"pciutils"}
            filtered_names = {
                "base-files",
                "libc6",
                "libkmod2",
                "libudev1",
                "zlib1g",
                # dependencies in focal
                "dpkg",
                "libacl1",
                "libbz2-1.0",
                "libcrypt1",
                "liblzma5",
                "libpcre2-8-0",
                "libselinux1",
                "libzstd1",
                "pci.ids",
                "perl-base",
                "tar",
            }

            apt_cache.mark_packages(package_names)
            apt_cache.unmark_packages(unmark_names=filtered_names)

            marked_packages = apt_cache.get_packages_marked_for_installation()
            assert sorted([name for name, _ in marked_packages]) == [
                "libpci3",
                "pciutils",
            ]

            names = []
            for pkg_name, pkg_version, dl_path in apt_cache.fetch_archives(
                fetch_dir_path
            ):
                names.append(pkg_name)
                assert dl_path.exists()
                assert dl_path.parent == fetch_dir_path
                assert isinstance(pkg_version, str)

            assert sorted(names) == ["libpci3", "pciutils"]

    def test_packages_without_candidate(self, tmpdir, mocker):
        class MockPackage:
            def __init__(self):
                self.name = "mock"
                self.marked_install = True
                self.candidate = None

        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)
        bad_pkg = cast(apt.package.Package, MockPackage())
        mocker.patch("apt.cache.Cache.get_changes", return_value=[bad_pkg])

        with AptCache(stage_cache=stage_cache) as apt_cache:
            with pytest.raises(errors.PackagesNotFound) as raised:
                apt_cache.get_packages_marked_for_installation()

        assert raised.value.packages == ["mock"]

    def test_marked_install_without_candidate(self, tmpdir, mocker):
        class MockPackage:
            def __init__(self):
                self.name = "mock"
                self.installed = False
                self.marked_install = False
                self.candidate = None

        bad_pkg = cast(apt.package.Package, MockPackage())

        with pytest.raises(errors.PackageNotFound) as raised:
            apt_cache._verify_marked_install(bad_pkg)

        assert raised.value.package_name == "mock"

    def test_unmark_packages_without_candidate(self, tmpdir, mocker):
        class MockPackage:
            def __init__(self):
                self.name = "mock"
                self.marked_install = True
                self.candidate = None

        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)
        bad_pkg = cast(apt.package.Package, MockPackage())
        mocker.patch("apt.cache.Cache.get_changes", return_value=[bad_pkg])

        with AptCache(stage_cache=stage_cache) as apt_cache:
            with pytest.raises(errors.PackageNotFound) as raised:
                apt_cache.unmark_packages({"mock"})

        assert raised.value.package_name == "mock"


class TestMockedApt:
    """Tests using mocked apt utility."""

    def test_configure(self, mocker):
        fake_apt = mocker.patch("craft_parts.packages.apt_cache.apt")

        AptCache().configure_apt("test_configure")
        # fmt: off
        assert fake_apt.mock_calls == [
            call.apt_pkg.config.set("Apt::Install-Recommends", "False"),
            call.apt_pkg.config.set("Acquire::AllowInsecureRepositories", "False"),
            call.apt_pkg.config.set("Dir::Etc::Trusted", "/etc/apt/trusted.gpg"),
            call.apt_pkg.config.set("Dir::Etc::TrustedParts", "/etc/apt/trusted.gpg.d/"),
            call.apt_pkg.config.set("Dir::State", "/var/lib/apt"),
            call.apt_pkg.config.clear("APT::Update::Post-Invoke-Success"),
        ]
        # fmt: on

    def test_configure_in_snap(self, mocker, tmpdir):
        fake_apt = mocker.patch("craft_parts.packages.apt_cache.apt")

        snap_dir = str(tmpdir)
        mocker.patch.dict(
            os.environ, {"SNAP_NAME": "test_configure_in_snap", "SNAP": snap_dir}
        )
        AptCache().configure_apt("test_configure_in_snap")
        # fmt: off
        assert fake_apt.mock_calls == [
            call.apt_pkg.config.set("Apt::Install-Recommends", "False"),
            call.apt_pkg.config.set("Acquire::AllowInsecureRepositories", "False"),
            call.apt_pkg.config.set("Dir", snap_dir + "/usr/lib/apt"),
            call.apt_pkg.config.set("Dir::Bin::methods", snap_dir + "/usr/lib/apt/methods/"),
            call.apt_pkg.config.set("Dir::Bin::solvers::", snap_dir + "/usr/lib/apt/solvers/"),
            call.apt_pkg.config.set("Dir::Bin::apt-key", snap_dir + "/usr/bin/apt-key"),
            call.apt_pkg.config.set("Apt::Key::gpgvcommand", snap_dir + "/usr/bin/gpgv"),
            call.apt_pkg.config.set("Dir::Etc::Trusted", "/etc/apt/trusted.gpg"),
            call.apt_pkg.config.set("Dir::Etc::TrustedParts", "/etc/apt/trusted.gpg.d/"),
            call.apt_pkg.config.set("Dir::State", "/var/lib/apt"),
            call.apt_pkg.config.clear("APT::Update::Post-Invoke-Success"),
        ]
        # fmt: on

    def test_stage_cache(self, tmpdir, mocker):
        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)
        fake_apt = mocker.patch("craft_parts.packages.apt_cache.apt")

        with AptCache(stage_cache=stage_cache) as _:
            pass

        assert fake_apt.mock_calls == [
            call.cache.Cache(rootdir=str(stage_cache), memonly=True),
            call.cache.Cache().close(),
        ]

    def test_host_cache_setup(self, mocker):
        fake_apt = mocker.patch("craft_parts.packages.apt_cache.apt")

        with AptCache() as _:
            pass

        assert fake_apt.mock_calls == [
            call.cache.Cache(rootdir="/"),
            call.cache.Cache().close(),
        ]


class TestAptReadonlyHostCache:
    """Host cache tests."""

    def test_host_is_package_valid(self):
        with AptCache() as apt_cache:
            assert apt_cache.is_package_valid("apt")
            assert apt_cache.is_package_valid("fake-news-bears") is False

    def test_host_get_installed_packages(self):
        with AptCache() as apt_cache:
            installed_packages = apt_cache.get_installed_packages()
            assert isinstance(installed_packages, dict)
            assert "apt" in installed_packages
            assert "fake-news-bears" not in installed_packages

    def test_host_get_installed_version(self):
        with AptCache() as apt_cache:
            assert isinstance(apt_cache.get_installed_version("apt"), str)
            assert apt_cache.get_installed_version("fake-news-bears") is None
