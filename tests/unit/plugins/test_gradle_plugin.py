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

import pytest
from overrides import override

from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.gradle_plugin import (
    GradlePlugin,
    GradlePluginEnvironmentValidator,
)


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def patch_succeed_cmd_validator(mocker):
    """Fixture to run successful command via self._execute for Maven plugin Validator."""

    class SuccessfulCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that always succeeds commands used by Maven plugin environment validator."""

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "java --version":
                return """openjdk 21.0.6 2025-01-21
OpenJDK Runtime Environment (build 21.0.6+7-Ubuntu-124.04.1)
OpenJDK 64-Bit Server VM (build 21.0.6+7-Ubuntu-124.04.1, mixed mode, sharing)"""
            if cmd in (
                "gradle --init-script ./gradle-plugin-init-script.gradle",
                "gradlew --init-script ./gradle-plugin-init-script.gradle",
            ):
                return ""
            if cmd in (
                "gradle printProjectJavaVersion",
                "./gradlew printProjectJavaVersion",
            ):
                return """
> Task :printJavaVersion
Project Java Version: 21

BUILD SUCCESSFUL in 395ms
1 actionable task: 1 executed
"""
            if cmd in ("gradle build", "./gradlew build"):
                return ""
            return super()._execute(cmd)

    mocker.patch.object(GradlePlugin, "validator_class", SuccessfulCmdValidator)


@pytest.mark.usefixtures("patch_succeed_cmd_validator")
def test_validate_dependency(dependency_fixture, part_info):
    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "gradle",
        output="""------------------------------------------------------------
Gradle 4.4.1
------------------------------------------------------------""",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )
    validator.validate_environment()
