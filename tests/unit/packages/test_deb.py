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

import contextlib
import subprocess
import textwrap
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock
from unittest.mock import call

import pytest
from craft_parts import ProjectInfo, callbacks, packages
from craft_parts.packages import deb, errors
from craft_parts.packages.deb_package import DebPackage

# pylint: disable=line-too-long
# pylint: disable=missing-class-docstring
# pylint: disable=unused-argument


@pytest.fixture(autouse=True)
def mock_env_copy():
    with mock.patch("os.environ.copy", return_value={}) as m:
        yield m


@pytest.fixture
def fake_all_packages_installed(mocker):
    mocker.patch(
        "craft_parts.packages.deb.Ubuntu._check_if_all_packages_installed",
        return_value=False,
    )


@pytest.fixture
def fake_dumb_terminal(mocker):
    return mocker.patch(
        "craft_parts.utils.os_utils.is_dumb_terminal", return_value=True
    )


@pytest.fixture(autouse=True)
def apt_update_cache():
    deb.Ubuntu.refresh_packages_list.cache_clear()


@pytest.fixture(autouse=True)
def cache_dirs(mocker, tmpdir):
    stage_cache_path = Path(tmpdir, "stage-cache")
    debs_path = Path(tmpdir, "debs")
    debs_path.mkdir(parents=True, exist_ok=False)

    mocker.patch(
        "craft_parts.packages.deb.get_cache_dirs",
        return_value=(stage_cache_path, debs_path),
    )

    @contextlib.contextmanager
    def fake_tempdir(*, suffix: str, **kwargs):
        temp_dir = Path(tmpdir, suffix)
        temp_dir.mkdir(exist_ok=True, parents=True)
        yield str(temp_dir)

    mocker.patch(
        "craft_parts.packages.deb.tempfile.TemporaryDirectory",
        new=fake_tempdir,
    )


class _FakeUbuntu:
    def __init__(self) -> None:
        self.apt_called = False

    @deb._apt_cache_wrapper
    def call_apt(self) -> None:
        self.apt_called = True


def test_fake_wrapper_apt_available(monkeypatch):
    monkeypatch.setattr(deb, "_APT_CACHE_AVAILABLE", True)

    fake_ubuntu = _FakeUbuntu()
    fake_ubuntu.call_apt()

    assert fake_ubuntu.apt_called is True


def test_fake_wrapper_apt_unavailable(monkeypatch):
    monkeypatch.setattr(deb, "_APT_CACHE_AVAILABLE", False)

    fake_ubuntu = _FakeUbuntu()
    with pytest.raises(errors.PackageBackendNotSupported):
        fake_ubuntu.call_apt()

    assert fake_ubuntu.apt_called is False


class TestPackages:
    def test_fetch_stage_packages(self, mocker, tmpdir, fake_apt_cache, fake_deb_run):
        # pylint: disable=unnecessary-dunder-call
        mocker.patch("os.geteuid", return_value=0)
        mocker.patch(
            "craft_parts.packages.deb._DEFAULT_FILTERED_STAGE_PACKAGES",
            {"filtered-pkg-1", "filtered-pkg-2"},
        )

        stage_cache_path, debs_path = deb.get_cache_dirs(tmpdir)
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=["fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
        )

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]
        assert fake_apt_cache.mock_calls == [
            call(stage_cache=stage_cache_path, stage_cache_arch="amd64"),
            call().__enter__(),
            call().__enter__().mark_packages({"fake-package"}),
            call().__enter__().unmark_packages({"filtered-pkg-1", "filtered-pkg-2"}),
            call().__enter__().fetch_archives(debs_path),
            call().__exit__(None, None, None),
        ]

        assert fetched_packages == ["fake-package=1.0"]

    def test_fetch_virtual_stage_package(
        self, tmpdir, mocker, fake_apt_cache, fake_deb_run
    ):
        mocker.patch("os.geteuid", return_value=0)
        _, debs_path = deb.get_cache_dirs(tmpdir)
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=["virtual-fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
        )

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]
        assert fetched_packages == ["fake-package=1.0"]

    def test_fetch_stage_package_with_deps(
        self, tmpdir, mocker, fake_apt_cache, fake_deb_run
    ):
        mocker.patch("os.geteuid", return_value=0)
        _, debs_path = deb.get_cache_dirs(tmpdir)
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_package_dep = debs_path / "fake-package-dep_1.0_all.deb"
        fake_package_dep.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package),
            ("fake-package-dep", "2.0", fake_package_dep),
        ]

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=["fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
        )

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]
        assert sorted(fetched_packages) == sorted(
            ["fake-package=1.0", "fake-package-dep=2.0"]
        )

    def test_fetch_stage_package_with_deps_with_package_filters(
        self, mocker, tmpdir, fake_apt_cache, fake_deb_run
    ):
        # pylint: disable=unnecessary-dunder-call
        mocker.patch("os.geteuid", return_value=0)
        mocker.patch(
            "craft_parts.packages.deb._DEFAULT_FILTERED_STAGE_PACKAGES",
            {"filtered-pkg-1"},
        )
        stage_cache_path, debs_path = deb.get_cache_dirs(tmpdir)
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_package_dep = debs_path / "fake-package-dep_2.0_all.deb"
        fake_package_dep.touch()
        other_fake_package = debs_path / "other-fake-package_1.0_all.deb"
        other_fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        package_names = ["fake-package", "other-fake-package"]

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=package_names,
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
            packages_filters={"fake-package-dep", "other-fake-package"},
        )

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]
        assert fake_apt_cache.mock_calls == [
            call(stage_cache=stage_cache_path, stage_cache_arch="amd64"),
            call().__enter__(),
            call().__enter__().mark_packages(set(package_names)),
            call()
            .__enter__()
            .unmark_packages(
                {"filtered-pkg-1", "fake-package-dep", "other-fake-package"}
            ),
            call().__enter__().fetch_archives(debs_path),
            call().__exit__(None, None, None),
        ]

        assert fetched_packages == ["fake-package=1.0"]

    def test_fetch_stage_package_empty_list(self, tmpdir, fake_apt_cache):
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = (
            []
        )

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=[],
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
        )

        assert fetched_packages == []

    def test_get_package_fetch_error(
        self, tmpdir, mocker, fake_apt_cache, fake_deb_run
    ):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.side_effect = errors.PackageFetchError(
            "foo"
        )

        with pytest.raises(errors.PackageFetchError) as raised:
            deb.Ubuntu.fetch_stage_packages(
                cache_dir=tmpdir,
                package_names=["fake-package"],
                stage_packages_path=Path(tmpdir),
                base="core",
                arch="amd64",
            )

        assert raised.value.message == "foo"
        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]

    def test_unpack_stage_packages_dont_normalize(self, tmpdir, mocker):
        packages_path = Path(tmpdir, "pkg")
        install_path = Path(tmpdir, "install")

        mock_normalize = mocker.patch("craft_parts.packages.normalize.normalize")

        # no packages in packages_path, no need to normalize
        packages_path.mkdir()
        install_path.mkdir()

        deb.Ubuntu.unpack_stage_packages(
            stage_packages_path=packages_path, install_path=install_path
        )

        assert mock_normalize.mock_calls == []

    def test_download_packages(self, fake_apt_cache, fake_deb_run, mocker):
        mocker.patch("os.geteuid", return_value=0)
        deb.Ubuntu.refresh_packages_list()
        deb.Ubuntu.download_packages(["package", "versioned-package=2.0"])

        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "--download-only",
                    "install",
                    "package",
                    "versioned-package=2.0",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
            ),
        ]


class TestBuildPackages:
    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_install_build_packages(self, fake_apt_cache, fake_deb_run, mocker):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0"),
            ("package-installed", "1.0"),
            ("versioned-package", "2.0"),
            ("dependency-package", "1.0"),
        ]

        deb.Ubuntu.refresh_packages_list()

        build_packages = deb.Ubuntu.install_packages(
            ["package-installed", "package", "versioned-package=2.0"]
        )

        assert build_packages == [
            "dependency-package=1.0",
            "package=1.0",
            "package-installed=1.0",
            "versioned-package=2.0",
        ]
        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "package",
                    "package-installed",
                    "versioned-package=2.0",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=subprocess.DEVNULL,
            ),
        ]

    def test_install_packages_empty_list(self, fake_apt_cache, fake_deb_run):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = (
            []
        )

        build_packages = deb.Ubuntu.install_packages([])

        assert build_packages == []
        assert fake_deb_run.mock_calls == []

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_already_installed_no_specified_version(
        self, fake_apt_cache, fake_deb_run, mocker
    ):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package-installed", "1.0")
        ]

        build_packages = deb.Ubuntu.install_packages(["package-installed"])

        assert build_packages == ["package-installed=1.0"]
        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "package-installed",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=-3,
            ),
        ]

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_already_installed_with_specified_version(
        self, fake_apt_cache, fake_deb_run, mocker
    ):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package-installed", "1.0")
        ]

        build_packages = deb.Ubuntu.install_packages(["package-installed=1.0"])

        assert build_packages == ["package-installed=1.0"]
        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "package-installed=1.0",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=-3,
            ),
        ]

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_already_installed_with_different_version(
        self, fake_apt_cache, fake_deb_run, mocker
    ):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("new-version", "3.0")
        ]

        deb.Ubuntu.refresh_packages_list()

        build_packages = deb.Ubuntu.install_packages(["new-version=3.0"])

        assert build_packages == ["new-version=3.0"]
        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "new-version=3.0",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=subprocess.DEVNULL,
            ),
        ]

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_install_virtual_build_package(self, fake_apt_cache, fake_deb_run, mocker):
        mocker.patch("os.geteuid", return_value=0)
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("resolved-virtual-package", "1.0")
        ]

        deb.Ubuntu.refresh_packages_list()

        build_packages = deb.Ubuntu.install_packages(["virtual-package"])

        assert build_packages == ["resolved-virtual-package=1.0"]
        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "virtual-package",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=subprocess.DEVNULL,
            ),
        ]

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_smart_terminal(
        self, fake_apt_cache, fake_deb_run, fake_dumb_terminal, mocker
    ):
        mocker.patch("os.geteuid", return_value=0)
        fake_dumb_terminal.return_value = False
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0")
        ]

        deb.Ubuntu.refresh_packages_list()

        deb.Ubuntu.install_packages(["package"])

        assert fake_deb_run.mock_calls == [
            call(["apt-get", "update"]),
            call(
                [
                    "apt-get",
                    "--no-install-recommends",
                    "-y",
                    "-oDpkg::Use-Pty=0",
                    "--allow-downgrades",
                    "install",
                    "package",
                ],
                env={
                    "DEBIAN_FRONTEND": "noninteractive",
                    "DEBCONF_NONINTERACTIVE_SEEN": "true",
                    "DEBIAN_PRIORITY": "critical",
                },
                stdin=subprocess.DEVNULL,
            ),
        ]

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_invalid_package_requested(self, fake_apt_cache, fake_deb_run):
        fake_apt_cache.return_value.__enter__.return_value.mark_packages.side_effect = (
            errors.PackageNotFound("package-invalid")
        )

        with pytest.raises(errors.BuildPackageNotFound):
            deb.Ubuntu.install_packages(["package-invalid"])

    @pytest.mark.usefixtures("fake_all_packages_installed")
    def test_broken_package_apt_install(self, fake_apt_cache, fake_deb_run, mocker):
        fake_apt_cache.return_value.__enter__.return_value.get_packages_marked_for_installation.return_value = [
            ("package", "1.0")
        ]
        mocker.patch("craft_parts.packages.deb.Ubuntu.refresh_packages_list")
        fake_deb_run.side_effect = CalledProcessError(100, "apt-get")

        with pytest.raises(errors.BuildPackagesNotInstalled) as raised:
            deb.Ubuntu.install_packages(["package=1.0"])
        assert raised.value.packages == ["package=1.0"]

    def test_refresh_packages_list(self, fake_deb_run, mocker):
        mocker.patch("os.geteuid", return_value=0)
        deb.Ubuntu.refresh_packages_list()

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]

    def test_refresh_packages_list_fails(self, fake_deb_run, mocker):
        mocker.patch("os.geteuid", return_value=0)
        fake_deb_run.side_effect = CalledProcessError(
            returncode=1, cmd=["apt-get", "update"]
        )

        with pytest.raises(errors.PackageListRefreshError):
            deb.Ubuntu.refresh_packages_list()

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]


@pytest.mark.parametrize(
    ("source_type", "pkgs"),
    [
        ("7zip", {"p7zip-full"}),
        ("bzr", {"bzr"}),
        ("git", {"git"}),
        ("hg", {"mercurial"}),
        ("mercurial", {"mercurial"}),
        ("rpm2cpio", {"rpm2cpio"}),
        ("rpm", {"rpm"}),
        ("subversion", {"subversion"}),
        ("svn", {"subversion"}),
        ("tar", {"tar"}),
        ("deb", set()),
        ("whatever-unknown", set()),
    ],
)
def test_packages_for_source_type(source_type, pkgs):
    assert deb.Ubuntu.get_packages_for_source_type(source_type) == pkgs


@pytest.fixture
def fake_dpkg_query(mocker):
    def dpkg_query(*args, **kwargs):
        # dpkg-query -S file_path
        if args[0][2] == "/bin/bash":
            return b"bash: /bin/bash\n"

        if args[0][2] == "/bin/sh":
            return (
                b"diversion by dash from: /bin/sh\n"
                b"diversion by dash to: /bin/sh.distrib\n"
                b"dash: /bin/sh\n"
            )

        raise CalledProcessError(
            1,
            f"dpkg-query: no path found matching pattern {args[0][2]}",
        )

    mocker.patch("subprocess.check_output", side_effect=dpkg_query)


class TestGetPackagesInBase:
    def test_hardcoded_bases(self):
        for base in ("core", "core16", "core18"):
            pkgs = [
                DebPackage.from_unparsed(p)
                for p in deb._DEFAULT_FILTERED_STAGE_PACKAGES
            ]
            assert deb.get_packages_in_base(base=base) == pkgs

    def test_package_list_from_dpkg_list(self, tmpdir, mocker):
        dpkg_list_path = Path(tmpdir, "dpkg.list")
        mocker.patch(
            "craft_parts.packages.deb._get_dpkg_list_path", return_value=dpkg_list_path
        )
        with dpkg_list_path.open("w") as dpkg_list_file:
            print(
                textwrap.dedent(
                    """\
            Desired=Unknown/Install/Remove/Purge/Hold
            | Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
            |/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
            ||/ Name                          Version                    Architecture Description
            +++-=============================-==========================-============-===========
            ii  adduser                       3.118ubuntu1               all          add and rem
            ii  apparmor                      2.13.3-7ubuntu2            amd64        user-space
            ii  apt                           2.0.1                      amd64        commandline
            ii  base-files                    11ubuntu4                  amd64        Debian base
            ii  base-passwd                   3.5.47                     amd64        Debian base
            ii  zlib1g:amd64                  1:1.2.11.dfsg-2ubuntu1     amd64        compression
            """
                ),
                file=dpkg_list_file,
            )

        assert deb.get_packages_in_base(base="core20") == [
            DebPackage("adduser"),
            DebPackage("apparmor"),
            DebPackage("apt"),
            DebPackage("base-files"),
            DebPackage("base-passwd"),
            DebPackage("zlib1g", arch="amd64"),
        ]

    def test_package_empty_list_from_missing_dpkg_list(self, tmpdir, mocker):
        dpkg_list_path = Path(tmpdir, "dpkg.list")
        mocker.patch(
            "craft_parts.packages.deb._get_dpkg_list_path", return_value=dpkg_list_path
        )

        assert deb.get_packages_in_base(base="core22") == []


class TestStagePackagesFilters:
    def setup_method(self):
        callbacks.unregister_all()
        packages.Repository.stage_packages_filters = None

    def teardown_class(self):
        callbacks.unregister_all()
        packages.Repository.stage_packages_filters = None

    def test_fetch_stage_packages_with_filtering(
        self, mocker, tmpdir, fake_apt_cache, fake_deb_run
    ):
        mocker.patch("os.geteuid", return_value=0)
        callbacks.register_stage_packages_filter(lambda x: ["base-pkg-1"])
        callbacks.register_stage_packages_filter(lambda x: ["base-pkg-2", "base-pkg-3"])

        # this is set in the execution prologue
        project_info = ProjectInfo(application_name="test", cache_dir=tmpdir)
        packages.Repository.stage_packages_filters = (
            callbacks.get_stage_packages_filters(project_info)
        )

        stage_cache_path, debs_path = deb.get_cache_dirs(tmpdir)
        fake_package = debs_path / "fake-package_1.0_all.deb"
        fake_package.touch()
        fake_apt_cache.return_value.__enter__.return_value.fetch_archives.return_value = [
            ("fake-package", "1.0", fake_package)
        ]

        fetched_packages = deb.Ubuntu.fetch_stage_packages(
            cache_dir=tmpdir,
            package_names=["fake-package"],
            stage_packages_path=Path(tmpdir),
            base="core",
            arch="amd64",
        )

        # pylint: disable=unnecessary-dunder-call

        assert fake_deb_run.mock_calls == [call(["apt-get", "update"])]
        assert fake_apt_cache.mock_calls == [
            call(stage_cache=stage_cache_path, stage_cache_arch="amd64"),
            call().__enter__(),
            call().__enter__().mark_packages({"fake-package"}),
            call()
            .__enter__()
            .unmark_packages({"base-pkg-1", "base-pkg-2", "base-pkg-3"}),
            call().__enter__().fetch_archives(debs_path),
            call().__exit__(None, None, None),
        ]

        # pylint: enable=unnecessary-dunder-call

        assert fetched_packages == ["fake-package=1.0"]


def test_get_filtered_stage_package_restricts_core20_ignore_filter(mocker):
    mock_get_packages_in_base = mocker.patch.object(deb, "get_packages_in_base")
    mock_get_packages_in_base.return_value = [
        DebPackage(name="foo"),
        DebPackage(name="foo2"),
        DebPackage(name="python3-attr"),
        DebPackage(name="python3-blinker"),
        DebPackage(name="python3-certifi"),
        DebPackage(name="python3-cffi-backend"),
        DebPackage(name="python3-chardet"),
        DebPackage(name="python3-configobj"),
        DebPackage(name="python3-cryptography"),
        DebPackage(name="python3-idna"),
        DebPackage(name="python3-importlib-metadata"),
        DebPackage(name="python3-jinja2"),
        DebPackage(name="python3-json-pointer"),
        DebPackage(name="python3-jsonpatch"),
        DebPackage(name="python3-jsonschema"),
        DebPackage(name="python3-jwt"),
        DebPackage(name="python3-lib2to3"),
        DebPackage(name="python3-markupsafe"),
        DebPackage(name="python3-more-itertools"),
        DebPackage(name="python3-netifaces"),
        DebPackage(name="python3-oauthlib"),
        DebPackage(name="python3-pyrsistent"),
        DebPackage(name="python3-pyudev"),
        DebPackage(name="python3-requests"),
        DebPackage(name="python3-requests-unixsocket"),
        DebPackage(name="python3-serial"),
        DebPackage(name="python3-six"),
        DebPackage(name="python3-urllib3"),
        DebPackage(name="python3-urwid"),
        DebPackage(name="python3-yaml"),
        DebPackage(name="python3-zipp"),
    ]

    filtered_names = deb._get_filtered_stage_package_names(
        base="core20",
        package_list=[],
        base_package_names=None,
    )

    assert filtered_names == {"foo", "foo2"}


def test_get_filtered_stage_package_empty_ignore_filter(mocker):
    mock_get_packages_in_base = mocker.patch.object(deb, "get_packages_in_base")
    mock_get_packages_in_base.return_value = [
        DebPackage(name="some-base-pkg"),
        DebPackage(name="some-other-base-pkg"),
    ]

    filtered_names = deb._get_filtered_stage_package_names(
        base="core00",
        package_list=[],
        base_package_names=None,
    )

    assert filtered_names == {"some-base-pkg", "some-other-base-pkg"}


def test_get_filtered_stage_package_core24(mocker):
    mock_get_packages_in_base = mocker.patch.object(deb, "get_packages_in_base")
    mock_get_packages_in_base.return_value = [
        DebPackage(name="some-package"),
        DebPackage(name="python3-cffi"),
        DebPackage(name="python3-cffi-backend"),
        DebPackage(name="python3-jsonschema"),
        DebPackage(name="python3-attr"),
    ]

    filtered_names = deb._get_filtered_stage_package_names(
        base="core24",
        package_list=[
            DebPackage(name="python3-cffi"),
            DebPackage(name="python3-jsonschema"),
        ],
        base_package_names=None,
    )

    # python3-cffi-backend and python3-attr must NOT be on the list of filtered
    # names, even though they are present in the core24 base.
    assert filtered_names == {"some-package"}
