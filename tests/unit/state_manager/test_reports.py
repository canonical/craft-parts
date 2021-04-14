# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest

from craft_parts.state_manager import reports
from craft_parts.steps import Step


@pytest.mark.parametrize(
    "step,source_updated,result",
    [
        (None, False, ""),
        (Step.BUILD, False, "'BUILD' step changed"),
        (None, True, "source changed"),
        (Step.STAGE, True, "'STAGE' step and source changed"),
    ],
)
def test_outdated_report(step, source_updated, result):
    report = reports.OutdatedReport(
        previous_step_modified=step, source_updated=source_updated
    )
    assert report.reason() == result
