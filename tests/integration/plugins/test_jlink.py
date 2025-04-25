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

import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors


@pytest.fixture
def build_test_jar(new_dir):
    Path("Test.java").write_text(
        """
            public class Test {
                public static void main(String[] args) {
                    new Embedded();
                }
            }
        """
    )
    Path("Embedded.java").write_text(
        """
            import javax.swing.*;
            public class Embedded {
                public Embedded() {
                    new JFrame("foo").setVisible(true);
                }
            }

        """
    )
    subprocess.run(
        ["javac", "Test.java", "Embedded.java"], check=True, capture_output=True
    )
    subprocess.run(
        ["jar", "cvf", "embedded.jar", "Embedded.class"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["jar", "cvf", "test.jar", "Test.class", "embedded.jar"],
        check=True,
        capture_output=True,
    )


@pytest.mark.usefixtures("build_test_jar")
def test_jlink_plugin_embedded_jar(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                source: .
                jlink-jars: ["test.jar"]
                after: ["stage-jar"]
            stage-jar:
                plugin: dump
                source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_jlink", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # java.desktop module should be included in the image
    assert len(list(Path(f"{new_dir}/stage/usr/lib/jvm/").rglob("libawt.so"))) > 0


def test_jlink_plugin_with_jar(new_dir, partitions):
    """Test that jlink produces tailored modules"""

    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                source: https://github.com/canonical/chisel-releases
                source-type: git
                source-branch: ubuntu-24.04
                jlink-jars: ["test.jar"]
                after: ["stage-jar"]
            stage-jar:
                plugin: dump
                source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    # build test jar
    Path("Test.java").write_text(
        """
            import javax.swing.*;
            public class Test {
                public static void main(String[] args) {
                    new JFrame("foo").setVisible(true);
                }
            }
        """
    )
    subprocess.run(["javac", "Test.java"], check=True, capture_output=True)
    subprocess.run(
        ["jar", "cvf", "test.jar", "Test.class"], check=True, capture_output=True
    )

    lf = LifecycleManager(
        parts, application_name="test_jlink", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # java.desktop module should be included in the image
    assert len(list(Path(f"{new_dir}/stage/usr/lib/jvm/").rglob("libawt.so"))) > 0


def test_jlink_plugin_bad_java_home(new_dir, partitions):
    """Test that jlink fails when JAVA_HOME is
    set incorrectly."""
    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                source: "https://github.com/canonical/chisel-releases"
                source-type: "git"
                source-branch: "ubuntu-24.04"
                build-environment:
                    - JAVA_HOME: /bad
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_jlink", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with pytest.raises(
        errors.PluginBuildError,
        match="Failed to run the build script for part 'my-part",
    ) as pe:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

    assert "Error: JAVA_HOME: '/bad/bin/java' is not an executable." in str(
        pe.value.stderr
    )


def test_jlink_plugin_java_home(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                source: "https://github.com/canonical/chisel-releases"
                source-type: "git"
                source-branch: "ubuntu-24.04"
                build-environment:
                    - JAVA_HOME: /usr/lib/jvm/java-17-openjdk-${CRAFT_ARCH_BUILD_FOR}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_jlink", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    java_release = Path(
        new_dir
        / f"stage/usr/lib/jvm/java-17-openjdk-{lf.project_info.target_arch}/release"
    )
    assert 'JAVA_VERSION="17.' in java_release.read_text()


def test_jlink_plugin_base(new_dir, partitions):
    """Test that jlink produces base image"""

    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                source: "https://github.com/canonical/chisel-releases"
                source-type: "git"
                source-branch: "ubuntu-24.04"
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_jlink", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    java = new_dir / "stage/usr/bin/java"
    assert java.isfile()
