# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
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

from subprocess import CalledProcessError
from unittest.mock import call

import pytest
from craft_parts.packages import errors
from craft_parts.packages.dnf import DNFRepository


def test_install_packages_simple(fake_dnf_run):
    """Simple and complete procedure when installing packages."""
    DNFRepository.install_packages(
        ["package-installed", "package", "versioned-package=2.0"]
    )
    assert fake_dnf_run.mock_calls == [
        call(
            [
                "dnf",
                "install",
                "-y",
                "package",
                "package-installed",
                "versioned-package=2.0",
            ]
        ),
    ]


def test_install_packages_empty_list(fake_dnf_run):
    """No packages given to install."""
    DNFRepository.install_packages([])
    fake_dnf_run.assert_not_called()


def test_install_packages_already_installed(fake_dnf_run, mocker):
    """Packages already installed, skipping actual installation."""
    mocker.patch.object(
        DNFRepository, "_check_if_all_packages_installed", return_value=True
    )
    DNFRepository.install_packages(["package-installed"])
    fake_dnf_run.assert_not_called()


def test_install_packages_refresh_not_requested(fake_dnf_run, mocker):
    """Packages installed but the dnf cache was not refreshed."""
    DNFRepository.install_packages(
        ["package-installed", "package"], refresh_package_cache=False
    )
    assert fake_dnf_run.mock_calls == [
        call(["dnf", "install", "-y", "package", "package-installed"]),
    ]


def test_install_packages_broken_package_dnf_install(fake_dnf_run):
    """The dnf installation goes wrong."""
    fake_dnf_run.side_effect = CalledProcessError(100, "dnf install -f")

    with pytest.raises(errors.BuildPackagesNotInstalled) as raised:
        DNFRepository.install_packages(["package=1.0"], refresh_package_cache=False)
    assert raised.value.packages == ["package=1.0"]


def test_refresh_packages_list(fake_dnf_run):
    """Check that refreshing the list of packages is a NOOP."""
    DNFRepository.refresh_packages_list()
    fake_dnf_run.assert_not_called()


@pytest.mark.parametrize(
    ("source_type", "packages"),
    [
        ("7zip", {"p7zip"}),
        ("git", {"git"}),
        ("hg", {"mercurial"}),
        ("mercurial", {"mercurial"}),
        ("rpm2cpio", set()),
        ("rpm", set()),
        ("subversion", {"subversion"}),
        ("svn", {"subversion"}),
        ("tar", {"tar"}),
        ("whatever-unknown", set()),
    ],
)
def test_packages_for_source_type(source_type, packages):
    assert DNFRepository.get_packages_for_source_type(source_type) == packages


def test_deb_source_type_not_implemented():
    with pytest.raises(NotImplementedError):
        DNFRepository.get_packages_for_source_type("deb")


def test_bzr_source_type_not_implemented():
    with pytest.raises(NotImplementedError):
        DNFRepository.get_packages_for_source_type("bzr")


# -- tests for methods left out of the DNFRepository MVP


def test_nomvp_configure():
    """Just a noop."""
    DNFRepository.configure("application package name")


def test_nomvp_get_package_libraries():
    """Not implemented, return empty."""
    with pytest.raises(NotImplementedError):
        assert DNFRepository.get_package_libraries("package name")


def test_nomvp_check_installed_packages():
    """Not implemented, return False."""
    assert DNFRepository._check_if_all_packages_installed(["foo", "bar"]) is False


def test_nomvp_download_packages():
    """Not implemented, raise an Error as it cannot be used."""
    with pytest.raises(NotImplementedError):
        assert DNFRepository.download_packages([])


def test_nomvp_is_package_installed():
    """Not implemented, return False."""
    assert DNFRepository.is_package_installed("testpackage") is False


def test_nomvp_get_installed_packages():
    """Not implemented, return empty."""
    assert len(DNFRepository.get_installed_packages()) == 0
