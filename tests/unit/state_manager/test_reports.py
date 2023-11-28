# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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
from craft_parts.state_manager import reports
from craft_parts.state_manager.reports import Dependency
from craft_parts.steps import Step


@pytest.mark.parametrize(
    ("step", "source_modified", "result"),
    [
        (None, False, ""),
        (Step.BUILD, False, "'BUILD' step changed"),
        (None, True, "source changed"),
        (Step.STAGE, True, "'STAGE' step and source changed"),
    ],
)
def test_outdated_report(step, source_modified, result):
    report = reports.OutdatedReport(
        previous_step_modified=step, source_modified=source_modified
    )
    assert report.reason() == result


@pytest.mark.parametrize(
    ("props", "opts", "deps", "result"),
    [
        (None, None, None, ""),
        (["a"], None, None, "'a' property changed"),
        (["a", "b"], None, None, "properties changed"),
        (None, ["c"], None, "'c' option changed"),
        (None, ["c", "d"], None, "options changed"),
        (["a"], ["c"], None, "options and properties changed"),
        (None, None, [Dependency("e", Step.STAGE)], "stage for part 'e' changed"),
        (
            None,
            None,
            [Dependency("e", Step.STAGE), Dependency("f", Step.STAGE)],
            "dependencies changed",
        ),
        (
            ["a"],
            None,
            [Dependency("e", Step.STAGE)],
            "dependencies and properties changed",
        ),
        (
            None,
            ["b"],
            [Dependency("e", Step.STAGE)],
            "dependencies and options changed",
        ),
        (
            ["a"],
            ["b"],
            [Dependency("e", Step.STAGE)],
            "dependencies, options, and properties changed",
        ),
    ],
)
def test_dirty_report(props, opts, deps, result):
    report = reports.DirtyReport(
        dirty_properties=props, dirty_project_options=opts, changed_dependencies=deps
    )
    assert report.reason() == result
