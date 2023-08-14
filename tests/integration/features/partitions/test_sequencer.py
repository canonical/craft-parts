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
import pytest

from tests.integration.sequencer import test_sequencer

# pylint: disable=unused-import
from tests.integration.sequencer.test_sequencer import pull_state  # noqa: F401

# pylint: enable=unused-import


@pytest.mark.usefixtures("new_dir")
class TestSequencerPlan(test_sequencer.TestSequencerPlan):
    """Verify action planning sanity with partitions enabled."""


@pytest.mark.usefixtures("new_dir", "pull_state")
class TestSequencerStates(test_sequencer.TestSequencerStates):
    """Check existing state loading."""
