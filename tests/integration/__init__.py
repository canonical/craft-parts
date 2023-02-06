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
"""Fixtures for all plugin tests to use."""

import pytest

from craft_parts.packages import deb


@pytest.fixture(autouse=True)
def clear_function_cache_after_run():
    yield
    deb.Ubuntu.refresh_packages_list.cache_clear()
    deb._run_dpkg_query_list_files.cache_clear()
    deb._run_dpkg_query_search.cache_clear()
