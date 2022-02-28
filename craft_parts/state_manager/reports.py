# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2018-2021 Canonical Ltd.
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

"""Provide a report on why a step is outdated."""

from dataclasses import dataclass
from typing import List, Optional

from craft_parts.steps import Step
from craft_parts.utils import formatting_utils


@dataclass(frozen=True)
class Dependency:
    """The part and step that are a prerequisite to another step."""

    part_name: str
    step: Step


class OutdatedReport:
    """The OutdatedReport class explains why a given step is outdated.

    An outdated step is defined to be a step that has run, but since doing so
    one of the following things have happened:

    - A step earlier in the lifecycle has run again.
    - The source on disk has been updated.
    """

    def __init__(
        self,
        *,
        previous_step_modified: Optional[Step] = None,
        source_modified: bool = False,
    ) -> None:
        """Create a new OutdatedReport.

        :param previous_step_modified: Step earlier in the lifecycle that has changed.
        :param source_modified: Whether the source changed on disk.
        """
        self.previous_step_modified = previous_step_modified
        self.source_modified = source_modified

    def reason(self) -> str:
        """Get summarized report.

        :return: Short summary of why the step is outdated.
        """
        reasons = []

        if self.previous_step_modified:
            reasons.append(f"{self.previous_step_modified.name!r} step")

        if self.source_modified:
            reasons.append("source")

        if not reasons:
            return ""

        return f'{formatting_utils.humanize_list(reasons, "and", "{}")} changed'


class DirtyReport:
    """The DirtyReport class explains why a given step is dirty.

    A dirty step is defined to be a step that has run, but since doing so one
    of the following things have happened:

    - One or more properties used by the step have changed.
    - One of more project options have changed.
    - One of more of its dependencies have been re-staged.
    """

    def __init__(
        self,
        *,
        dirty_properties: Optional[List[str]] = None,
        dirty_project_options: Optional[List[str]] = None,
        changed_dependencies: Optional[List[Dependency]] = None,
    ) -> None:
        """Create a new DirtyReport.

        :param dirty_properties: Properties that have changed.
        :param dirty_project_options: Project options that have changed.
        :param changed_dependencies: Dependencies that have changed.
        """
        self.dirty_properties = dirty_properties
        self.dirty_project_options = dirty_project_options
        self.changed_dependencies = changed_dependencies

    # pylint: disable=too-many-branches
    def reason(self) -> str:
        """Get summarized report.

        :return: Short summary of why the part is dirty.
        """
        reasons = []

        reasons_count = 0
        if self.dirty_properties:
            reasons_count += 1
        if self.dirty_project_options:
            reasons_count += 1
        if self.changed_dependencies:
            reasons_count += 1

        if self.dirty_properties:
            # Be specific only if this is the only reason
            if reasons_count > 1 or len(self.dirty_properties) > 1:
                reasons.append("properties")
            else:
                reasons.append(f"{self.dirty_properties[0]!r} property")

        if self.dirty_project_options:
            # Be specific only if this is the only reason
            if reasons_count > 1 or len(self.dirty_project_options) > 1:
                reasons.append("options")
            else:
                reasons.append(f"{self.dirty_project_options[0]!r} option")

        if self.changed_dependencies:
            # Be specific only if this is the only reason
            if reasons_count > 1 or len(self.changed_dependencies) > 1:
                reasons.append("dependencies")
            else:
                part_name = self.changed_dependencies[0].part_name
                step_name = self.changed_dependencies[0].step.name.lower()
                reasons.append(f"{step_name} for part {part_name!r}")

        if not reasons:
            return ""

        return f'{formatting_utils.humanize_list(reasons, "and", "{}")} changed'

    # pylint: enable=too-many-branches
