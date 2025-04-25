# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2024 Canonical Ltd.
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
"""Tests that plugin behaviour is unchanged with partitions enabled."""
# Allow redefinition in order to include parent tests below.
# mypy: disable-error-code="no-redef"

# These wildcard imports make pytest run any non-overridden plugin tests here.
# pylint: disable=wildcard-import, unused-import, function-redefined, unused-wildcard-import
# pyright: reportGeneralTypeIssues=false
from tests.integration.plugins.test_ant import *  # noqa: F403
from tests.integration.plugins.test_application_plugin import *  # noqa: F403
from tests.integration.plugins.test_autotools import *  # noqa: F403
from tests.integration.plugins.test_cmake import *  # noqa: F403
from tests.integration.plugins.test_dotnet import *  # noqa: F403
from tests.integration.plugins.test_dump import *  # noqa: F403
from tests.integration.plugins.test_go import *  # noqa: F403
from tests.integration.plugins.test_make import *  # noqa: F403
from tests.integration.plugins.test_maven import *  # noqa: F403
from tests.integration.plugins.test_meson import *  # noqa: F403
from tests.integration.plugins.test_npm import *  # noqa: F403
from tests.integration.plugins.test_python import *  # noqa: F403
from tests.integration.plugins.test_rust import *  # noqa: F403
from tests.integration.plugins.test_scons import *  # noqa: F403
from tests.integration.plugins.test_validate_environment import *  # type: ignore[assignment] # noqa: F403

# pylint: enable=wildcard-import
