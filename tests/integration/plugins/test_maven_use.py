# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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
import logging
import shutil
import subprocess
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step

SOURCE_DIR = Path(__file__).parent / "test_maven_use"


def test_maven_use_plugin(new_dir, partitions, monkeypatch):
    project_dir = Path(new_dir) / "project"
    shutil.copytree(SOURCE_DIR / "simple", project_dir)
    monkeypatch.chdir(project_dir)
    work_dir = Path(new_dir)
    parts_yaml = (project_dir / "parts.yaml").read_text()
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="simple",
        cache_dir=new_dir,
        work_dir=work_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # Check that jar and pom and where "deployed" to the backstage
    backstage = lf.project_info.backstage_dir

    expected_jar = backstage / "maven-use/org/starcraft/add/2.2.0/add-2.2.0.jar"
    assert expected_jar.is_file()

    expected_pom = backstage / "maven-use/org/starcraft/add/2.2.0/add-2.2.0.pom"
    assert expected_pom.is_file()


def test_maven_use_plugin_self_contained(new_dir, partitions, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    project_dir = Path(new_dir) / "project"
    shutil.copytree(SOURCE_DIR / "self-contained", project_dir)
    monkeypatch.chdir(project_dir)
    work_dir = Path(new_dir)
    parts_yaml = (project_dir / "parts.yaml").read_text()
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_go",
        cache_dir=new_dir,
        work_dir=work_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    jar_dir = lf.project_info.prime_dir / "jar"
    jars = {i.name for i in jar_dir.iterdir()}
    # Only the two jars produced by the main part
    # (the shade plugin creates the "original-*" one)
    assert jars == {"hello-world-0.1.0.jar", "original-hello-world-0.1.0.jar"}

    jar = jar_dir / "hello-world-0.1.0.jar"
    assert jar.is_file()

    output = subprocess.check_output(["java", "-jar", str(jar)], text=True)
    assert output == "1 plus 1 equals 2\n"

    # Get the version of the maven-shade-plugin that was effectively used, since it
    # comes from the archive and will be updated with time.
    shaded_plugin = Path(
        "/usr/share/maven-repo/org/apache/maven/plugins/maven-shade-plugin/"
    )
    assert shaded_plugin.is_dir()
    shaded_version = next(shaded_plugin.iterdir()).name

    # Check that we logged the version replacements.
    log = caplog.text
    expected_bumps = [
        ("org.starcraft.add", "2.0.0", "2.2.0"),
        ("org.starcraft.print-addition", "1.0.0", "1.1.0"),
        ("org.starcraft.parent", "1.1.0", "1.0.0"),
    ]

    # Check that versions are adjusted as necessary
    for artifact, old, new in expected_bumps:
        assert f"Updating version of '{artifact}' from '{old}' to '{new}'" in log

    # Check that missing versions are filled in by what's available
    assert (
        f"Setting version of 'org.apache.maven.plugins.maven-shade-plugin' to '{shaded_version}'"
        in log
    )
