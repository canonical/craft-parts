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


class TestAptStageCache:
    """Make sure the stage cache is working correctly.

    This are expensive tests, but is much more valuable than using mocks.
    When adding tests, consider adding it to test_stage_packages(), or
    create mocks.
    """

    @pytest.mark.slow
    def test_stage_packages(self, tmpdir):
        fetch_dir_path = Path(tmpdir, "debs")
        fetch_dir_path.mkdir(exist_ok=True, parents=True)
        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)

        AptCache.configure_apt("test_stage_packages")
        with AptCache(stage_cache=stage_cache) as cache:
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
                # dependencies in jammy
                "gcc-13-base",
                "libgcc-s1",
            }

            cache.mark_packages(package_names)
            cache.unmark_packages(unmark_names=filtered_names)

            marked_packages = cache.get_packages_marked_for_installation()
            assert sorted([name for name, _ in marked_packages]) == [
                "libpci3",
                "pciutils",
            ]

            names = []
            for pkg_name, pkg_version, dl_path in cache.fetch_archives(fetch_dir_path):
                names.append(pkg_name)
                assert dl_path.exists()
                assert dl_path.parent == fetch_dir_path
                assert isinstance(pkg_version, str)

            assert sorted(names) == ["libpci3", "pciutils"]

    def test_mark_packages_version_interdependency(self, tmpdir, mocker):
        """Test that mark_packages pins all versions before calling mark_install.

        Simulates libnvinfer-dev depending on libnvinfer10 with an exact
        version constraint. Without the two-pass fix, iteration order can
        cause mark_install to fail because the dependency's candidate has
        not been pinned yet.
        """
        # Declarative description of packages and their versions/deps.
        # "default" is the candidate apt would pick without pinning.
        # "deps" maps version -> list of (pkg_name, relation, version).
        package_specs = {
            "libnvinfer-dev": {
                "versions": ["10.14.1", "10.15.1"],
                "default": "10.15.1",
                "deps": {"10.14.1": [("libnvinfer10", "=", "10.14.1")]},
            },
            "libnvinfer10": {
                "versions": ["10.14.1", "10.15.1"],
                "default": "10.15.1",
                "deps": {},
            },
        }

        # Build mock objects from specs.
        pkg_mocks = {}  # name -> mock Package
        ver_mocks = {}  # (name, version_str) -> mock Version

        for name, spec in package_specs.items():
            for ver_str in spec["versions"]:
                v = mocker.MagicMock()
                v.version = ver_str
                v.__str__ = lambda self, s=ver_str: s
                v.dependencies = []
                ver_mocks[(name, ver_str)] = v

            versions_dict = {vs: ver_mocks[(name, vs)] for vs in spec["versions"]}
            pkg = mocker.MagicMock(
                spec=[
                    "name",
                    "installed",
                    "marked_install",
                    "candidate",
                    "versions",
                    "mark_install",
                    "mark_auto",
                ],
            )
            pkg.name = name
            pkg.installed = None
            pkg.marked_install = False
            pkg.candidate = ver_mocks[(name, spec["default"])]
            pkg.versions = mocker.MagicMock()
            pkg.versions.get = versions_dict.get
            pkg.mark_auto.side_effect = lambda auto: None
            pkg_mocks[name] = pkg

        # Wire up dependency objects on versions.
        for name, spec in package_specs.items():
            for ver_str, dep_list in spec.get("deps", {}).items():
                groups = []
                for dep_name, dep_rel, dep_ver in dep_list:
                    dep = mocker.MagicMock()
                    dep.name = dep_name
                    dep.relation = dep_rel
                    dep.version = dep_ver
                    dep.target_versions = [ver_mocks[(dep_name, dep_ver)]]
                    groups.append([dep])
                ver_mocks[(name, ver_str)].dependencies = groups

        # Simulate apt's mark_install: fail when a dependency's candidate
        # doesn't match the required version.
        def make_mark_install(pkg):
            def side_effect(auto_fix=True, from_user=True):
                for dep_group in pkg.candidate.dependencies if pkg.candidate else []:
                    for d in dep_group:
                        dep_pkg = pkg_mocks.get(d.name)
                        if dep_pkg is None:
                            continue
                        if (
                            dep_pkg.candidate is None
                            or dep_pkg.candidate.version != d.version
                        ):
                            pkg.candidate = None
                            pkg.marked_install = False
                            return
                pkg.marked_install = True

            return side_effect

        for pkg in pkg_mocks.values():
            pkg.mark_install.side_effect = make_mark_install(pkg)

        # Mock cache.
        mock_cache = mocker.MagicMock()
        mock_cache.is_virtual_package.return_value = False
        mock_cache.__contains__ = lambda self, n: n in pkg_mocks
        mock_cache.__getitem__ = lambda self, n: pkg_mocks[n]
        mocker.patch("apt.cache.Cache", return_value=mock_cache)

        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)

        with AptCache(stage_cache=stage_cache) as cache:
            cache.mark_packages(
                {
                    "libnvinfer-dev=10.14.1",
                    "libnvinfer10=10.14.1",
                }
            )

        for pkg in pkg_mocks.values():
            assert pkg.marked_install is True

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

        with AptCache(stage_cache=stage_cache) as cache:
            with pytest.raises(errors.PackagesNotFound) as raised:
                cache.get_packages_marked_for_installation()

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

        with AptCache(stage_cache=stage_cache) as cache:
            with pytest.raises(errors.PackageNotFound) as raised:
                cache.unmark_packages({"mock"})

        assert raised.value.package_name == "mock"


class TestMockedApt:
    """Tests using mocked apt utility."""

    def test_configure(self, mocker):
        fake_apt_pkg = mocker.patch("craft_parts.packages.apt_cache.apt_pkg")

        AptCache().configure_apt("test_configure")
        # fmt: off
        assert fake_apt_pkg.mock_calls == [
            call.config.set("Apt::Install-Recommends", "False"),
            call.config.set("Acquire::AllowInsecureRepositories", "False"),
            call.config.set("Dir::Etc::Trusted", "/etc/apt/trusted.gpg"),
            call.config.set("Dir::Etc::TrustedParts", "/etc/apt/trusted.gpg.d/"),
            call.config.set("Dir::State", "/var/lib/apt"),
            call.config.clear("APT::Update::Post-Invoke-Success"),
        ]
        # fmt: on

    def test_configure_in_snap(self, mocker, tmpdir):
        fake_apt_pkg = mocker.patch("craft_parts.packages.apt_cache.apt_pkg")

        snap_dir = str(tmpdir)
        mocker.patch.dict(
            os.environ, {"SNAP_NAME": "test_configure_in_snap", "SNAP": snap_dir}
        )
        AptCache().configure_apt("test_configure_in_snap")
        # fmt: off
        assert fake_apt_pkg.mock_calls == [
            call.config.set("Apt::Install-Recommends", "False"),
            call.config.set("Acquire::AllowInsecureRepositories", "False"),
            call.config.set("Dir", snap_dir + "/usr/lib/apt"),
            call.config.set("Dir::Bin::methods", snap_dir + "/usr/lib/apt/methods/"),
            call.config.set("Dir::Bin::solvers::", snap_dir + "/usr/lib/apt/solvers/"),
            call.config.set("Dir::Bin::apt-key", snap_dir + "/usr/bin/apt-key"),
            call.config.set("Apt::Key::gpgvcommand", snap_dir + "/usr/bin/gpgv"),
            call.config.set("Dir::Etc::Trusted", "/etc/apt/trusted.gpg"),
            call.config.set("Dir::Etc::TrustedParts", "/etc/apt/trusted.gpg.d/"),
            call.config.set("Dir::State", "/var/lib/apt"),
            call.config.clear("APT::Update::Post-Invoke-Success"),
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
        with AptCache() as cache:
            assert cache.is_package_valid("apt")
            assert cache.is_package_valid("fake-news-bears") is False

    def test_host_get_installed_packages(self):
        with AptCache() as cache:
            installed_packages = cache.get_installed_packages()
            assert isinstance(installed_packages, dict)
            assert "apt" in installed_packages
            assert "fake-news-bears" not in installed_packages

    def test_host_get_installed_version(self):
        with AptCache() as cache:
            assert isinstance(cache.get_installed_version("apt"), str)
            assert cache.get_installed_version("fake-news-bears") is None


def test_ignore_unreadable_files(tmp_path):
    unreadable = tmp_path / "unreadable"
    unreadable.touch(000)
    readable = tmp_path / "readable"
    readable.touch()

    result = apt_cache._ignore_unreadable_files(tmp_path, ["unreadable", "readable"])

    assert result == ["unreadable"]
