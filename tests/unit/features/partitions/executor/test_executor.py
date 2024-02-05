# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

from tests.unit.executor import test_executor


class TestExecutor(test_executor.TestExecutor):
    """Verify executor class methods with partitions."""


class TestPackages(test_executor.TestPackages):
    """Verify package installation during the execution phase with partitions."""


class TestExecutionContext(test_executor.TestExecutionContext):
    """Verify execution context methods with partitions."""
