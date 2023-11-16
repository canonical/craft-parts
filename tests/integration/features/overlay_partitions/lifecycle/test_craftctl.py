# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

# Allow redefinition in order to include parent tests below.
# mypy: disable-error-code="no-redef"
import pytest

# Make pytest run any non-overridden chisel tests here with partitions enabled.
from tests.integration.lifecycle.test_craftctl import *  # noqa: F403


@pytest.fixture(autouse=True)
def _setup_feature(_setup):
    return
