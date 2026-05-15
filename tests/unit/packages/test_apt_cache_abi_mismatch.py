# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""Regression tests for https://github.com/canonical/craft-parts/issues/1554.

When a snap built on core24 (bundling libapt-pkg.so.6.0 / python-apt 2.7.x)
runs on Ubuntu 26.04 (which ships libapt-pkg.so.7.0 / apt 3.x), the apt
cache returned by python-apt is empty due to the ABI mismatch. craft-parts
then raises BuildPackageNotFound for packages that DO exist on the host,
instead of detecting the broken/empty cache and raising a more helpful error.
"""

from unittest.mock import MagicMock, patch

import pytest
from craft_parts.packages import deb, errors
from craft_parts.packages.apt_cache import AptCache


class _EmptyCache:
    """Simulate an apt cache that returns no packages (ABI mismatch scenario).

    When python-apt is compiled against a different libapt-pkg ABI than the
    host's, ``apt.cache.Cache(rootdir="/")`` opens successfully but contains
    zero packages because it cannot parse the host's binary cache.
    """

    def __contains__(self, item: str) -> bool:
        return False

    def __iter__(self):
        return iter([])

    def __len__(self) -> int:
        return 0

    def is_virtual_package(self, name: str) -> bool:
        return False

    def get_providing_packages(self, name: str) -> list:
        return []

    def get_changes(self) -> list:
        return []

    def close(self) -> None:
        pass


class TestAbiMismatchEmptyCache:
    """Tests for issue #1554: BuildPackageNotFound with ABI-mismatched apt."""

    def test_mark_packages_raises_buildpackagenotfound_on_empty_cache(self):
        """Demonstrate the bug: an empty cache causes BuildPackageNotFound.

        When the apt cache is empty due to an ABI mismatch (e.g. core24 snap
        on Ubuntu 26.04), mark_packages raises PackageNotFound for every
        package, which deb.py wraps as BuildPackageNotFound.

        This test documents the current (broken) behaviour: valid packages
        like 'python3-dev' are reported as not found.
        """
        cache = AptCache()
        cache.cache = _EmptyCache()

        with pytest.raises(errors.PackageNotFound, match="python3-dev"):
            cache.mark_packages({"python3-dev"})

    def test_is_package_valid_returns_false_on_empty_cache(self):
        """Demonstrate the bug: all packages appear invalid with an empty cache."""
        cache = AptCache()
        cache.cache = _EmptyCache()

        assert cache.is_package_valid("python3-dev") is False

    def test_get_installed_packages_returns_empty_on_empty_cache(self):
        """An empty cache reports zero installed packages."""
        cache = AptCache()
        cache.cache = _EmptyCache()

        assert cache.get_installed_packages() == {}

    def test_empty_cache_should_not_raise_buildpackagenotfound(self):
        """Regression test: an empty/broken cache should NOT produce BuildPackageNotFound.

        The fix for #1554 should detect that the cache is empty or broken
        (e.g. due to ABI mismatch between the snap's python-apt and the host's
        libapt-pkg) and raise a more specific error or fall back to a
        subprocess-based package check, rather than claiming the package
        doesn't exist.

        This test FAILS before the fix is applied and should PASS after.
        """
        mock_cache = _EmptyCache()

        with patch("craft_parts.packages.deb.AptCache") as mock_apt_cache_cls:
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=MagicMock())
            ctx.__enter__.return_value.cache = mock_cache
            # Simulate mark_packages raising PackageNotFound (current behaviour)
            ctx.__enter__.return_value.mark_packages.side_effect = (
                errors.PackageNotFound("python3-dev")
            )
            mock_apt_cache_cls.return_value = ctx

            with patch(
                "craft_parts.packages.deb.Ubuntu._check_if_all_packages_installed",
                return_value=False,
            ):
                # The bug: this raises BuildPackageNotFound for a valid package.
                # After the fix, this should NOT raise BuildPackageNotFound;
                # it should either succeed (by falling back to apt-get) or
                # raise an error specifically about the cache/ABI mismatch.
                try:
                    deb.Ubuntu.install_packages(["python3-dev"])
                except errors.BuildPackageNotFound:
                    pytest.fail(
                        "BuildPackageNotFound should not be raised when the apt "
                        "cache is empty/broken due to an ABI mismatch (issue #1554). "
                        "The fix should detect the broken cache and either fall back "
                        "to subprocess-based package resolution or raise a more "
                        "specific error about the ABI mismatch."
                    )
                except Exception:
                    # Any other exception is acceptable for now — the important
                    # thing is that BuildPackageNotFound is not raised for
                    # packages that actually exist on the host.
                    pass
