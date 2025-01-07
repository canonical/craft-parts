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

import glob
import subprocess
import textwrap
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step


def test_jlink_plugin_other_java(new_dir, partitions):
    """Test that jlink produces image for the different Java version"""

    parts_yaml = textwrap.dedent(
        """
        parts:
            my-part:
                plugin: jlink
                jlink-java-version: 17
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

    assert bool(glob.glob(str(new_dir / "stage/usr/lib/jvm/java-17-*")))
    assert not bool(glob.glob(str(new_dir / "stage/usr/lib/jvm/java-21-*")))


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
