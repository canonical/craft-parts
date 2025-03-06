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
def install_spring_boot_project(tmp_path, new_dir):
    # Using default CLI arguments to generate the project. Without specifying
    # all the arguments, the CLi becomes interactive.
    subprocess.check_call(
        [
            "sudo",  # requires sudo in tmp path
            "devpack-for-spring",
            "boot",
            "start",
            "--path",
            "app",
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
def cleanup_java_11():
    yield
    subprocess.check_call(["sudo", "apt", "remove", "openjdk-11-jdk", "-y"])
    subprocess.check_call(["sudo", "apt", "autoremove", "-y"])


@pytest.fixture
def cleanup_java_17():
    yield
    subprocess.check_call(["sudo", "apt", "remove", "openjdk-17-jdk", "-y"])
    subprocess.check_call(["sudo", "apt", "autoremove", "-y"])


@pytest.fixture
def spring_boot_plugin_parts():
    parts_yaml = textwrap.dedent(
        """
        parts:
            deps-setup:
                plugin: nil
                build-packages:
                - openjdk-17-jdk
            my-part:
                plugin: spring-boot
                source: app
                after: [deps-setup]
        """
    )
    return yaml.safe_load(parts_yaml)


@pytest.mark.usefixtures("install_spring_boot_project", "cleanup_java_11")
def test_spring_boot_plugin_project_java_mismatch(new_dir, partitions):
    """Spring boot project and system incompatible Java version."""
    parts_yaml = textwrap.dedent(
        """
        parts:
            deps-setup:
                plugin: nil
                build-packages:
                - openjdk-11-jdk
            my-part:
                plugin: spring-boot
                source: app
                after: [deps-setup]
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
    new_dir, partitions, spring_boot_plugin_parts
):
    """Spring boot project has mvnw but is not executable."""
    os.chmod(
        new_dir / "app/mvnw",
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


@pytest.mark.usefixtures("install_spring_boot_project", "cleanup_java_17")
def test_spring_boot_plugin_project_build_wrapper_not_exists(
    new_dir, partitions, spring_boot_plugin_parts
):
    """Spring boot project has no mvnw or gradlew wrapper."""
    (new_dir / "app/mvnw").remove()
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
