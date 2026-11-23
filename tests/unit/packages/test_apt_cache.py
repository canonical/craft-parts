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
import subprocess
from pathlib import Path
from typing import cast
from unittest.mock import call

import apt.package
import apt_pkg
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
            package_names = ["pciutils"]
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

    def test_mark_packages_version_interdependency(self, tmpdir, mocker):  # noqa: PLR0915
        """Test that mark_packages pins all versions before calling mark_install.

        Simulates libnvinfer-dev depending on libnvinfer10 with an exact
        version constraint. Without the two-pass fix, iteration order can
        cause mark_install to fail because the dependency's candidate has
        not been pinned yet.
        """
        # Create Version mocks directly.
        nvinfer10_v14 = mocker.MagicMock()
        nvinfer10_v14.version = "10.14.1"
        nvinfer10_v14.dependencies = []

        nvinfer10_v15 = mocker.MagicMock()
        nvinfer10_v15.version = "10.15.1"
        nvinfer10_v15.dependencies = []

        # libnvinfer-dev 10.14.1 depends on libnvinfer10 (= 10.14.1)
        dep = mocker.MagicMock()
        dep.name = "libnvinfer10"
        dep.relation = "="
        dep.version = "10.14.1"
        dep.target_versions = [nvinfer10_v14]

        nvinfer_dev_v14 = mocker.MagicMock()
        nvinfer_dev_v14.version = "10.14.1"
        nvinfer_dev_v14.dependencies = [[dep]]

        nvinfer_dev_v15 = mocker.MagicMock()
        nvinfer_dev_v15.version = "10.15.1"
        nvinfer_dev_v15.dependencies = []

        # Create Package mocks directly.
        # Default candidates are v15 (the "wrong" version apt would pick).
        pkg_attrs = [
            "name",
            "installed",
            "marked_install",
            "candidate",
            "versions",
            "mark_install",
            "mark_auto",
        ]

        nvinfer_dev_pkg = mocker.MagicMock(spec=pkg_attrs)
        nvinfer_dev_pkg.name = "libnvinfer-dev"
        nvinfer_dev_pkg.installed = None
        nvinfer_dev_pkg.marked_install = False
        nvinfer_dev_pkg.candidate = nvinfer_dev_v15
        nvinfer_dev_pkg.versions = mocker.MagicMock()
        nvinfer_dev_pkg.versions.get = {
            "10.14.1": nvinfer_dev_v14,
            "10.15.1": nvinfer_dev_v15,
        }.get
        nvinfer_dev_pkg.mark_auto.side_effect = lambda auto: None

        nvinfer10_pkg = mocker.MagicMock(spec=pkg_attrs)
        nvinfer10_pkg.name = "libnvinfer10"
        nvinfer10_pkg.installed = None
        nvinfer10_pkg.marked_install = False
        nvinfer10_pkg.candidate = nvinfer10_v15
        nvinfer10_pkg.versions = mocker.MagicMock()
        nvinfer10_pkg.versions.get = {
            "10.14.1": nvinfer10_v14,
            "10.15.1": nvinfer10_v15,
        }.get
        nvinfer10_pkg.mark_auto.side_effect = lambda auto: None

        pkg_mocks = {
            "libnvinfer-dev": nvinfer_dev_pkg,
            "libnvinfer10": nvinfer10_pkg,
        }

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
                [
                    "libnvinfer-dev=10.14.1",
                    "libnvinfer10=10.14.1",
                ]
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

    def test_fetch_archives_error_includes_uri(self, tmpdir, mocker):
        class MockCandidate:
            def __init__(self):
                self.uri = "http://example.com/pool/mock_1.0_amd64.deb"

            def fetch_binary(self, destdir, progress=None, allow_unauthenticated=None):
                raise apt.package.FetchError(
                    "The item '/root/.cache/mock_1.0_amd64.deb' could not be fetched: "
                    "Connection failed [IP: 185.125.190.81 80]"
                )

        class MockPackage:
            def __init__(self):
                self.name = "mock"
                self.candidate = MockCandidate()

        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)
        bad_pkg = cast(apt.package.Package, MockPackage())
        mocker.patch("apt.cache.Cache.get_changes", return_value=[bad_pkg])

        with AptCache(stage_cache=stage_cache) as cache:
            with pytest.raises(errors.PackageFetchError) as raised:
                cache.fetch_archives(Path(tmpdir, "debs"))

        assert raised.value.url == "http://example.com/pool/mock_1.0_amd64.deb"
        assert (
            raised.value.brief
            == "Failed to fetch package from http://example.com/pool/mock_1.0_amd64.deb."
        )
        assert raised.value.details == (
            "The item '/root/.cache/mock_1.0_amd64.deb' could not be fetched: "
            "Connection failed [IP: 185.125.190.81 80]"
        )

    def test_fetch_archives_error_without_uri(self, tmpdir, mocker):
        class MockCandidate:
            def __init__(self):
                self.uri = None

            def fetch_binary(self, destdir, progress=None, allow_unauthenticated=None):
                raise apt.package.FetchError("download failed")

        class MockPackage:
            def __init__(self):
                self.name = "mock"
                self.candidate = MockCandidate()

        stage_cache = Path(tmpdir, "cache")
        stage_cache.mkdir(exist_ok=True, parents=True)
        bad_pkg = cast(apt.package.Package, MockPackage())
        mocker.patch("apt.cache.Cache.get_changes", return_value=[bad_pkg])

        with AptCache(stage_cache=stage_cache) as cache:
            with pytest.raises(errors.PackageFetchError) as raised:
                cache.fetch_archives(Path(tmpdir, "debs"))

        assert raised.value.url is None
        assert raised.value.brief == "Failed to fetch package."
        assert raised.value.details == "download failed"

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


@pytest.fixture
def sandbox_user():
    """Set apt's sandbox user to _apt for the test and restore it afterwards."""
    old = apt_pkg.config.find("APT::Sandbox::User")
    apt_pkg.config.set("APT::Sandbox::User", "_apt")
    yield "_apt"
    apt_pkg.config.set("APT::Sandbox::User", old)


@pytest.fixture
def as_root(mocker):
    mocker.patch("os.geteuid", return_value=0)
    return mocker.patch("pwd.getpwnam", return_value=mocker.Mock(pw_uid=42, pw_gid=43))


@pytest.mark.usefixtures("sandbox_user")
class TestSandboxUserCanWrite:
    def test_not_root(self, mocker, tmp_path):
        mocker.patch("os.geteuid", return_value=1000)
        mock_run = mocker.patch("subprocess.run")

        assert apt_cache._sandbox_user_can_write(tmp_path)
        mock_run.assert_not_called()

    @pytest.mark.parametrize("user", ["", "root"])
    def test_sandbox_disabled(self, mocker, as_root, tmp_path, user):
        apt_pkg.config.set("APT::Sandbox::User", user)
        mock_run = mocker.patch("subprocess.run")

        assert apt_cache._sandbox_user_can_write(tmp_path)
        mock_run.assert_not_called()

    def test_sandbox_user_missing(self, mocker, as_root, tmp_path):
        as_root.side_effect = KeyError("_apt")
        mock_run = mocker.patch("subprocess.run")

        assert apt_cache._sandbox_user_can_write(tmp_path)
        mock_run.assert_not_called()

    def test_writable(self, mocker, as_root, tmp_path):
        probe = tmp_path / "tmp.abc123"
        probe.touch()
        mock_run = mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                [], returncode=0, stdout=f"{probe}\n", stderr=""
            ),
        )

        assert apt_cache._sandbox_user_can_write(tmp_path)
        mock_run.assert_called_once_with(
            ["mktemp", "-p", str(tmp_path)],
            user=42,
            group=43,
            extra_groups=[],
            capture_output=True,
            text=True,
            check=False,
        )
        as_root.assert_called_once_with("_apt")
        assert not probe.exists(), "probe file must be cleaned up"

    def test_not_writable(self, mocker, as_root, tmp_path):
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                [], returncode=1, stdout="", stderr="Permission denied"
            ),
        )

        assert not apt_cache._sandbox_user_can_write(tmp_path)

    def test_cannot_switch_user(self, mocker, as_root, tmp_path):
        mocker.patch("subprocess.run", side_effect=PermissionError("setuid"))

        assert not apt_cache._sandbox_user_can_write(tmp_path)


@pytest.mark.usefixtures("sandbox_user")
class TestFetchArchivesSandbox:
    """The sandbox is only disabled when apt's sandbox user cannot write."""

    @staticmethod
    def _mock_package(seen_users, error=None):
        class MockCandidate:
            uri = "http://example.com/pool/mock_1.0_amd64.deb"
            version = "1.0"

            def fetch_binary(self, destdir, progress=None, allow_unauthenticated=None):
                seen_users.append(apt_pkg.config.find("APT::Sandbox::User"))
                if error:
                    raise error
                return str(Path(destdir, "mock_1.0_amd64.deb"))

        class MockPackage:
            name = "mock"
            candidate = MockCandidate()

        return cast(apt.package.Package, MockPackage())

    @pytest.mark.parametrize(
        ("writable", "expected_user"), [(True, "_apt"), (False, "root")]
    )
    def test_sandbox_user_during_fetch(self, tmp_path, mocker, writable, expected_user):
        seen: list[str] = []
        mocker.patch(
            "apt.cache.Cache.get_changes", return_value=[self._mock_package(seen)]
        )
        mocker.patch.object(apt_cache, "_sandbox_user_can_write", return_value=writable)
        stage_cache = tmp_path / "cache"
        stage_cache.mkdir()

        with AptCache(stage_cache=stage_cache) as cache:
            fetched = cache.fetch_archives(tmp_path / "debs")

        assert seen == [expected_user]
        assert fetched == [("mock", "1.0", tmp_path / "debs" / "mock_1.0_amd64.deb")]
        assert apt_pkg.config.find("APT::Sandbox::User") == "_apt"

    def test_sandbox_user_restored_on_error(self, tmp_path, mocker):
        seen: list[str] = []
        error = apt.package.FetchError("download failed")
        mocker.patch(
            "apt.cache.Cache.get_changes",
            return_value=[self._mock_package(seen, error=error)],
        )
        mocker.patch.object(apt_cache, "_sandbox_user_can_write", return_value=False)
        stage_cache = tmp_path / "cache"
        stage_cache.mkdir()

        with AptCache(stage_cache=stage_cache) as cache:
            with pytest.raises(errors.PackageFetchError):
                cache.fetch_archives(tmp_path / "debs")

        assert seen == ["root"]
        assert apt_pkg.config.find("APT::Sandbox::User") == "_apt"
