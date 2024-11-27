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

import subprocess
import textwrap
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step


def run_build(new_dir, partitions, application):
    source_location = Path(__file__).parent / "test_maven"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {source_location}
            stage-packages: [openjdk-21-jre-headless]
            build-packages:
                - openjdk-8-jdk-headless
                - openjdk-17-jdk-headless
                - openjdk-21-jdk-headless
            override-build: |
                echo ${{JAVA_HOME:-default}} > $CRAFT_PART_INSTALL/java_home
                craftctl default
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name=application,
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    return lf.project_info.prime_dir


def test_java_plugin(new_dir, partitions):
    """This test validates that java plugin sets JAVA_HOME.
    The JAVA_HOME should be set according to the following rules:
    - Latest version of Java VM is selected
    - Selected Java VM should be able to compile test test file

    The test installs multiple Java VMs and asserts that JAVA_HOME
    is set to Java 21.
    """

    prime_dir = run_build(new_dir, partitions, "test_java_plugin")
    java_binary = prime_dir / "bin/java"
    assert java_binary.is_file()

    content = (prime_dir / "java_home").read_text()
    assert "21" in content

    output = subprocess.check_output(
        [str(java_binary), "-jar", f"{prime_dir}/jar/HelloWorld-1.0.jar"], text=True
    )
    assert output.strip() == "Hello from Maven-built Java"
