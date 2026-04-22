# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

"""Regression test for libapt ABI mismatch (Issue #1554).

When a snap built on core24 (bundling python-apt 2.7.x / libapt-pkg.so.6.0)
runs on Ubuntu 26.04 (which ships apt 3.x / libapt-pkg.so.7.0), craft-parts
raises BuildPackageNotFound for packages that do exist on the system.

This test verifies that the apt cache can be opened and packages can be found.
It is expected to:
- PASS on Ubuntu 24.04 (Noble) with the noble python-apt (dev-noble group).
- FAIL on Ubuntu 26.04 (Resolute) with the noble python-apt (dev-noble group),
  reproducing the ABI mismatch bug.

The failure may manifest either as:
- An ImportError (libapt-pkg.so.6.0 not found on the system), or
- An empty apt cache (cache binary format version mismatch), which causes
  BuildPackageNotFound to be raised for any package.

See: https://github.com/canonical/craft-parts/issues/1554
"""

import pytest
from craft_parts.packages.apt_cache import AptCache

_BUILD_PACKAGES = ("python3-dev", "python3-venv")


@pytest.fixture(autouse=True)
def configure_apt_cache() -> None:
    """Configure apt before each test in this module."""
    AptCache.configure_apt("test-apt-abi-mismatch")


def test_apt_cache_is_not_empty() -> None:
    """Verify that the host apt cache is not empty.

    An empty cache indicates that python-apt cannot read the system's apt
    package lists, which is a symptom of an ABI mismatch between the loaded
    python-apt and the system's libapt-pkg library.
    """
    with AptCache() as cache:
        cache_size = len(cache.cache)
        assert cache_size > 0, (
            f"The apt package cache is empty (contains {cache_size} packages). "
            "This indicates an ABI mismatch between python-apt and the "
            "system's libapt-pkg library. The python-apt version in use was "
            "likely compiled against a different libapt-pkg SONAME than the "
            "one installed on this system."
        )


@pytest.mark.parametrize("package_name", _BUILD_PACKAGES)
def test_build_package_found_in_apt_cache(package_name: str) -> None:
    """Verify that common build packages are found in the apt cache.

    This is a regression test for issue #1554: BuildPackageNotFound for valid
    packages when a snap uses core24 on Ubuntu 26.04 (libapt ABI mismatch).

    When python-apt compiled against libapt-pkg.so.6.0 is used on Ubuntu 26.04
    (which ships libapt-pkg.so.7.0), the apt cache either fails to load or
    returns no results, causing is_package_valid() to return False for every
    package. craft-parts then raises BuildPackageNotFound even though the
    package exists on the system.
    """
    with AptCache() as cache:
        assert cache.is_package_valid(package_name), (
            f"Package {package_name!r} was not found in the apt cache, even "
            "though it is a valid package on this system. This reproduces "
            "the ABI mismatch bug from issue #1554: python-apt cannot "
            "correctly read the host's apt package lists."
        )
