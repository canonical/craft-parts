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

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors


@pytest.fixture
def source_location(new_dir):
    return new_dir / "test_spring_boot"


@pytest.fixture
def install_spring_boot_project(source_location):
    # Using default CLI arguments to generate the project. Without specifying
    # all the arguments, the CLi becomes interactive.
    subprocess.check_call(
        [
            "devpack-for-spring",
            "boot",
            "start",
            "--path",
            str(source_location),
            "--project",
            "maven-project",
            "--language",
            "java",
            "--boot-version",
            "3.4.2",
            "--version",
            "0.0.1",
            "--group",
            "com.example",
            "--artifact",
            "spring-boot",
            "--name",
            "spring-boot",
            "--description",
            "demo",
            "--package-name",
            "com.example.demo",
            "--dependencies",
            "web",
            "--packaging",
            "jar",
            "--java-version",
            "17",
        ]
    )


@pytest.fixture
def spring_boot_plugin_parts(source_location):
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
            deps-setup:
                plugin: nil
                build-packages:
                - openjdk-17-jdk
            my-part:
                plugin: spring-boot
                source: {source_location}
                after: [deps-setup]
                build-environment:
                - JAVA_HOME: /usr/lib/jvm/java-17-openjdk-${{CRAFT_ARCH_BUILD_FOR}}
        """
    )
    return yaml.safe_load(parts_yaml)


@pytest.mark.usefixtures("install_spring_boot_project")
def test_spring_boot_plugin_project_java_mismatch(new_dir, partitions, source_location):
    """Spring boot project and system incompatible Java version."""
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
            deps-setup:
                plugin: nil
                build-packages:
                - openjdk-11-jdk
            my-part:
                plugin: spring-boot
                source: {source_location}
                after: [deps-setup]
                build-environment:
                - JAVA_HOME: /usr/lib/jvm/java-11-openjdk-${{CRAFT_ARCH_BUILD_FOR}}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_spring_boot",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with pytest.raises(
        errors.PluginBuildError,
        match="Failed to run the build script for part 'my-part",
    ) as pe:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    assert "Project requires Java version" in str(pe.value.stderr)


@pytest.mark.usefixtures("install_spring_boot_project")
def test_spring_boot_plugin_output_jar(new_dir, partitions, spring_boot_plugin_parts):
    lf = LifecycleManager(
        spring_boot_plugin_parts,
        application_name="test_spring_boot",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Output jars should exist in staging directory
    assert len(list(Path(f"{new_dir}/stage/").rglob("*.jar"))) > 0


@pytest.mark.usefixtures("install_spring_boot_project")
def test_spring_boot_plugin_project_build_wrapper_not_executable(
    new_dir, partitions, spring_boot_plugin_parts, source_location
):
    """Spring boot project has mvnw but is not executable."""
    os.chmod(
        source_location / "mvnw",
        # Read write permissions for users, groups and others but not executable
        stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH,
    )
    lf = LifecycleManager(
        spring_boot_plugin_parts,
        application_name="test_spring_boot",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with pytest.raises(
        errors.PluginBuildError,
        match="Failed to run the build script for part 'my-part",
    ) as pe:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    assert '"mvnw" found but not executable' in str(pe.value.stderr)


@pytest.mark.usefixtures("install_spring_boot_project")
def test_spring_boot_plugin_project_build_wrapper_not_exists(
    new_dir, partitions, spring_boot_plugin_parts, source_location
):
    """Spring boot project has no mvnw or gradlew wrapper."""
    (source_location / "mvnw").remove()
    lf = LifecycleManager(
        spring_boot_plugin_parts,
        application_name="test_spring_boot",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with pytest.raises(
        errors.PluginBuildError,
        match="Failed to run the build script for part 'my-part",
    ) as pe:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    assert 'Neither "mvnw" nor "gradlew" found.' in str(pe.value.stderr)
