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

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from craft_parts import LifecycleManager, Step
from craft_parts.infos import ProjectInfo


@pytest.fixture
def local_proxy_url():
    conf_file = Path("proxy.conf")
    conf_file.write_text(
        """
Port 8888
Timeout 600
DefaultErrorFile "/usr/share/tinyproxy/default.html"
StatFile "/usr/share/tinyproxy/stats.html"
LogFile "/var/log/tinyproxy/tinyproxy.log"
LogLevel Info
PidFile "/run/tinyproxy/tinyproxy.pid"
MaxClients 100
Allow 127.0.0.1
Allow ::1
ViaProxyName "tinyproxy"
    """,
        encoding="utf-8",
    )
    proc = subprocess.Popen(["sudo", "tinyproxy", "-d", str(conf_file)])
    yield "http://localhost:8888"
    proc.kill()


@pytest.fixture
def use_gradlew(request):
    if request.param:
        yield request.param
        return
    source_location = Path(__file__).parent / "test_gradle"
    gradlew_file = source_location / "gradlew"
    gradlew_file = gradlew_file.rename(f"{source_location}/gradlew.backup")
    yield request.param
    gradlew_file.rename(f"{source_location}/gradlew")


# Parametrization of using gradle vs gradlew is not applied since gradle cannot
# run init scripts at the time of writing (2025-04-2) due to the version provided
# by Ubuntu packages archive being too low (4.4.1).
def test_gradle_plugin_gradlew(new_dir, partitions, local_proxy_url):
    part_name = "foo"
    source_location = Path(__file__).parent / "test_gradle"
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          {part_name}:
            plugin: gradle
            gradle-task: testWrite build
            gradle-init-script: init.gradle
            source: {source_location}
            build-packages: [gradle, openjdk-21-jdk]
            build-environment:
                - JAVA_HOME: /usr/lib/jvm/java-21-openjdk-${{CRAFT_ARCH_BUILD_FOR}}
                - http_proxy: {local_proxy_url}
                - https_proxy: {local_proxy_url}
                - GRADLE_USER_HOME: {new_dir}/parts/{part_name}/build/.gradle
            stage-packages: [openjdk-21-jdk]
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_ant",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    _test_core_gradle_plugin_build_output(project_info=lf.project_info)
    # generated by the init.gradle testWrite task
    assert (lf.project_info.dirs.parts_dir / f"{part_name}/build" / "test.txt").exists()


@pytest.mark.parametrize("use_gradlew", [False], indirect=True)
def test_gradle_plugin_gradle(new_dir, partitions, use_gradlew):
    part_name = "foo"
    source_location = Path(__file__).parent / "test_gradle"
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          {part_name}:
            plugin: gradle
            gradle-task: build
            source: {source_location}
            build-packages: [gradle, openjdk-21-jdk]
            build-environment:
            - JAVA_HOME: /usr/lib/jvm/java-21-openjdk-${{CRAFT_ARCH_BUILD_FOR}}
            - GRADLE_USER_HOME: {new_dir}/parts/{part_name}/build/.gradle
            stage-packages: [openjdk-21-jdk]
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_ant",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    _test_core_gradle_plugin_build_output(project_info=lf.project_info)


def _test_core_gradle_plugin_build_output(project_info: ProjectInfo) -> None:
    prime_dir = project_info.prime_dir
    java_binary = Path(prime_dir, "bin", "java")
    jar_file = Path(prime_dir, "jar", "build-1.0.jar")
    assert java_binary.is_file()
    assert jar_file.is_file(), f"Jarfile not found in {list(jar_file.parent.iterdir())}"

    output = subprocess.check_output(
        [str(java_binary), "-jar", f"{prime_dir}/jar/build-1.0.jar"], text=True
    )
    assert output.strip() == "Hello from Gradle-built Java"
