# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
from craft_parts import Part, PartInfo, ProjectInfo
from craft_parts.plugins.gradle_use_plugin import GradleUsePlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def self_contained_part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"build-attributes": ["self-contained"]}),
    )


def test_gradle_task_should_not_be_defined():
    with pytest.raises(ValidationError) as exc:
        GradleUsePlugin.properties_class.unmarshal(
            {"source": ".", "gradle-task": "build"}
        )

    assert "gradle-task is not supported" in exc.value.errors()[0]["msg"]


def test_get_build_commands(
    part_info,
):
    properties = GradleUsePlugin.properties_class.unmarshal(
        {
            "source": ".",
        }
    )
    plugin = GradleUsePlugin(properties=properties, part_info=part_info)

    publish_init_script = part_info.part_build_subdir / ".parts" / "publish.init.gradle"
    assert plugin.get_build_commands() == (
        [
            f"gradle publish --init-script {publish_init_script} --no-daemon",
            f'find {part_info.part_build_subdir} -name "gradle-wrapper.jar" -type f -delete',
        ]
    )


def test_get_build_commands_self_contained(self_contained_part_info):
    properties = GradleUsePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradleUsePlugin(properties=properties, part_info=self_contained_part_info)

    gradle_cmd = plugin.get_build_commands()[0]

    publish_init_script = (
        self_contained_part_info.part_build_subdir / ".parts" / "publish.init.gradle"
    )
    assert f"--init-script {publish_init_script} --offline" in gradle_cmd
    assert "maven-publish" in publish_init_script.read_text()
