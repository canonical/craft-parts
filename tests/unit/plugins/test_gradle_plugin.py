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

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from craft_parts import Part, PartInfo, ProjectInfo, errors
from craft_parts.plugins.gradle_plugin import (
    GradlePlugin,
    GradlePluginEnvironmentValidator,
)
from overrides import override


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def patch_succeed_cmd_validator(mocker):
    """Fixture to run successful command via self._execute for Gradle plugin Validator."""

    class SuccessfulCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that always succeeds commands used by Gradle plugin environment validator."""

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


@pytest.fixture
def setup_gradlew_file(part_info):
    """Setup gradlew file to test plugin when project gradlew file exists."""
    gradlew_file = part_info.part_src_dir / Path("./gradlew")
    gradlew_file.parent.mkdir(parents=True, exist_ok=True)
    gradlew_file.touch(exist_ok=True)
    yield
    gradlew_file.unlink()


@pytest.fixture
def setup_init_script_file(part_info):
    """Setup gradle init script file to test plugin when project gradlew init script is passed."""
    init_script_file = part_info.part_src_dir / "init.gradle"
    init_script_file.parent.mkdir(parents=True, exist_ok=True)
    init_script_file.touch(exist_ok=True)
    yield
    init_script_file.unlink()


@pytest.mark.usefixtures("patch_succeed_cmd_validator")
def test_validate_environment(dependency_fixture, part_info):
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


def test_validate_environment_missing_gradle(part_info):
    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)

    validator = plugin.validator_class(
        part_name="my-part", env="PATH=/foo", properties=properties
    )

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert raised.value.reason == "'gradle' not found"


def test_validate_environment_gradle_version_invalid(part_info, dependency_fixture):
    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "gradle",
        output="Invalid version output",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert "invalid gradle version" in raised.value.reason


def test_validate_environment_invalid_init_script_path(part_info, dependency_fixture):
    properties = GradlePlugin.properties_class.unmarshal(
        {"source": ".", "gradle-init-script": "not-exists.gradle"}
    )
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "gradle",
        output="Gradle 4.4.1",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert (
        "gradle init script option supplied but file not found" in raised.value.reason
    )


@pytest.mark.usefixtures("setup_gradlew_file")
def test_validate_environment_java_version_check_fail(
    mocker, part_info, dependency_fixture
):
    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "./gradlew",
        output="Gradle 4.4.1",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    class FailCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that fails commands used by Gradle plugin environment validator."""

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "java --version":
                raise subprocess.CalledProcessError(1, cmd=cmd, output="test fail")
            return super()._execute(cmd)

    mocker.patch.object(GradlePlugin, "validator_class", FailCmdValidator)

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert "failed to check java version" in raised.value.reason


def test_validate_environment_java_version_check_invalid(
    mocker, part_info, dependency_fixture
):
    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "./gradlew",
        output="Gradle 4.4.1",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    class FailCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that fails commands used by Gradle plugin environment validator."""

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "java --version":
                return "invalid java version"
            return super()._execute(cmd)

    mocker.patch.object(GradlePlugin, "validator_class", FailCmdValidator)

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert "failed to check java version" in raised.value.reason


@pytest.mark.usefixtures("setup_gradlew_file")
def test_validate_environment_gradle_init_script_fail(
    mocker, part_info, dependency_fixture
):
    class FailCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that fails commands used by Gradle plugin environment validator."""

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "java --version":
                return """openjdk 21.0.6 2025-01-21
OpenJDK Runtime Environment (build 21.0.6+7-Ubuntu-124.04.1)
OpenJDK 64-Bit Server VM (build 21.0.6+7-Ubuntu-124.04.1, mixed mode, sharing)"""
            if (
                cmd
                == "./gradlew --init-script /tmp/gradle-plugin-init-script.gradle \
gradle-plugin-printProjectJavaVersion 2>&1"
            ):
                raise subprocess.CalledProcessError(1, cmd, "test error")
            return super()._execute(cmd)

    mocker.patch.object(GradlePlugin, "validator_class", FailCmdValidator)

    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "./gradlew",
        output="Gradle 4.4.1",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert "failed to execute project java version check" in raised.value.reason


@pytest.mark.usefixtures("setup_gradlew_file")
def test_validate_environment_gradle_project_version_check_fail(
    mocker, part_info, dependency_fixture
):
    tmp_dir = tempfile.gettempdir()

    class FailCmdValidator(GradlePluginEnvironmentValidator):
        """A validator that fails commands used by Gradle plugin environment validator."""

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "java --version":
                return """openjdk 21.0.6 2025-01-21
OpenJDK Runtime Environment (build 21.0.6+7-Ubuntu-124.04.1)
OpenJDK 64-Bit Server VM (build 21.0.6+7-Ubuntu-124.04.1, mixed mode, sharing)"""
            if cmd in (
                f"gradle --init-script {tmp_dir}/gradle-plugin-init-script.gradle",
                f"./gradlew --init-script {tmp_dir}/gradle-plugin-init-script.gradle",
            ):
                return ""
            if cmd in (
                "gradle printProjectJavaVersion",
                "./gradlew printProjectJavaVersion",
            ):
                return "Not a valid project Java version output."
            return super()._execute(cmd)

    mocker.patch.object(GradlePlugin, "validator_class", FailCmdValidator)

    properties = GradlePlugin.properties_class.unmarshal({"source": "."})
    plugin = GradlePlugin(properties=properties, part_info=part_info)
    gradle = dependency_fixture(
        "./gradlew",
        output="Gradle 4.4.1",
    )

    validator = plugin.validator_class(
        part_name="my-part", env=f"PATH={str(gradle.parent)}", properties=properties
    )

    with pytest.raises(errors.PluginEnvironmentValidationError) as raised:
        validator.validate_environment()

    assert "failed to parse project java version:" in raised.value.reason


@pytest.mark.parametrize(
    ("task", "parameters", "init_script", "init_script_params", "expected_commands"),
    [
        ("build", [], "", [], ["gradle build"]),
        ("pack", [], "", [], ["gradle pack"]),
        ("pack", ["--parameter=value"], "", [], ["gradle pack --parameter=value"]),
        (
            "pack",
            [],
            "init.gradle",
            [],
            ["gradle --init-script init.gradle", "gradle pack"],
        ),
    ],
)
@pytest.mark.usefixtures("setup_init_script_file")
def test_get_build_commands(
    part_info, task, parameters, init_script, init_script_params, expected_commands
):
    properties = GradlePlugin.properties_class.unmarshal(
        {
            "source": ".",
            "gradle-task": task,
            "gradle-parameters": parameters,
            "gradle-init-script": init_script,
            "gradle-init-script-parameters": init_script_params,
        }
    )
    plugin = GradlePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        [*expected_commands, *plugin._get_java_post_build_commands()]
    )


@pytest.mark.usefixtures("setup_gradlew_file")
def test_get_build_commands_use_gradlew(part_info, dependency_fixture):
    properties = GradlePlugin.properties_class.unmarshal(
        {"source": ".", "gradle-task": "build"}
    )
    dependency_fixture(
        "./gradlew",
        output="Gradle 4.4.1",
    )
    plugin = GradlePlugin(properties=properties, part_info=part_info)

    assert plugin.get_build_commands() == (
        ["./gradlew build", *plugin._get_java_post_build_commands()]
    )


@pytest.mark.usefixtures("setup_gradlew_file")
def test_proxy_settings_configured(part_info, mocker):
    mocker.patch.object(
        os,
        "environ",
        {
            "no_proxy": "test_no_proxy_url",
            "http_proxy": "https://user:password@test_proxy_http_url.com:3128",
            "https_proxy": "https://user:password@test_proxy_https_url.com:3128",
        },
    )
    properties = GradlePlugin.properties_class.unmarshal(
        {"source": ".", "gradle-task": "build"}
    )

    plugin = GradlePlugin(properties=properties, part_info=part_info)

    plugin._setup_proxy()

    gradle_properties = (
        plugin._part_info.part_build_dir / ".gradle/gradle.properties"
    ).read_text(encoding="utf-8")
    assert "systemProp.http.proxyHost=test_proxy_http_url.com" in gradle_properties
    assert "systemProp.http.proxyPort=3128" in gradle_properties
    assert "systemProp.http.proxyUser=user" in gradle_properties
    assert "systemProp.http.proxyPassword=password" in gradle_properties
    assert "systemProp.http.nonProxyHosts=test_no_proxy_url" in gradle_properties
    assert "systemProp.https.proxyHost=test_proxy_https_url.com" in gradle_properties
    assert "systemProp.https.proxyPort=3128" in gradle_properties
    assert "systemProp.https.proxyUser=user" in gradle_properties
    assert "systemProp.https.proxyPassword=password" in gradle_properties
    assert "systemProp.https.nonProxyHosts=test_no_proxy_url" in gradle_properties
