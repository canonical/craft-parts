# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2025 Canonical Ltd.
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
from craft_parts import Part, PartInfo, ProjectInfo, errors
from craft_parts.plugins.maven_plugin import MavenPlugin
from pydantic import ValidationError


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.mark.parametrize(
    "mvn_version", [("\x1b[1mApache Maven 3.6.3\x1b[m"), ("Apache Maven 3.6.3")]
)
def test_validate_environment(dependency_fixture, part_info, mvn_version):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)
    mvn = dependency_fixture("mvn", output=mvn_version)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(mvn.parent)}", properties=properties
    )
    validator.validate_environment()


def test_validate_environment_missing_mvn(part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'mvn' not found"


def test_validate_environment_broken_mvn(dependency_fixture, part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)
    ant = dependency_fixture("mvn", broken=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ant.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'mvn' failed with error code 33"


def test_validate_environment_invalid_mvn(dependency_fixture, part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)
    ant = dependency_fixture("mvn", invalid=True)

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(ant.parent)}", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "invalid maven version ''"


def test_validate_environment_with_maven_part(part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    validator.validate_environment(part_dependencies=["maven-deps"])


def test_validate_environment_without_maven_part(part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )
    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment(part_dependencies=[])

    assert raised.value.reason == (
        "'mvn' not found and part 'my-part' does not depend on a part named "
        "'maven-deps' that would satisfy the dependency"
    )


def test_get_build_snaps_and_packages(part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_snaps() == set()
    assert plugin.get_build_packages() == set()


def test_get_build_environment(part_info):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)
    env = plugin.get_build_environment()
    assert "JAVA_HOME" in env
    assert len(env) == 1


def test_missing_parameters():
    with pytest.raises(ValidationError) as raised:
        MavenPlugin.properties_class.unmarshal({})
    err = raised.value.errors()
    assert len(err) == 1
    assert err[0]["loc"] == ("source",)
    assert err[0]["type"] == "missing"


def test_get_build_commands(part_info, maven_settings_path):
    properties = MavenPlugin.properties_class.unmarshal({"source": "."})
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        [
            f"mvn package -s {maven_settings_path}",
            *plugin._get_java_post_build_commands(),
        ]
    )


def test_get_build_commands_with_parameters(part_info, maven_settings_path):
    properties = MavenPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "maven-parameters": ["-Dprop1=1", "-c"],
        }
    )
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        [
            f"mvn package -s {maven_settings_path} -Dprop1=1 -c",
            *plugin._get_java_post_build_commands(),
        ]
    )


def test_get_build_commands_use_maven_wrapper(part_info, maven_settings_path):
    properties = MavenPlugin.properties_class.unmarshal(
        {
            "source": ".",
            "maven-use-wrapper": True,
        }
    )
    plugin = MavenPlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        [
            """[ -e ${CRAFT_PART_BUILD_WORK}/mvnw ] || {
>&2 echo 'mvnw file not found, refer to plugin documentation: \
https://canonical-craft-parts.readthedocs-hosted.com/en/latest/\
common/craft-parts/reference/plugins/maven_plugin.html'; exit 1;
}""",
            "${CRAFT_PART_BUILD_WORK}/mvnw package" + f" -s {maven_settings_path}",
            *plugin._get_java_post_build_commands(),
        ]
    )
