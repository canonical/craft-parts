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

import pytest
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
        application_name="test_maven_use_self_contained",
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


def test_maven_use_with_modules(
    new_dir: Path,
    partitions: list[str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    project_dir = Path(new_dir) / "project"
    shutil.copytree(SOURCE_DIR / "multi-module", project_dir)
    monkeypatch.chdir(project_dir)
    work_dir = Path(new_dir)
    parts_yaml = (project_dir / "parts.yaml").read_text()
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="test_maven_use_with_modules",
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

    log = caplog.text
    assert "Setting version of 'org.starcraft.subsubmod' to '1.0.0'" in log

    assert (
        "Discovered poms for part 'java-dep-top': [pom.xml, java-dep-submod/pom.xml, java-dep-submod/java-dep-subsubmod/pom.xml]"
        in log
    )
    assert "Discovered poms for part 'java-main-part': [pom.xml]" in log

    maven_repo = lf.project_info.dirs.backstage_dir / "maven-use"
    bs_dirs: set[str] = set()
    bs_jars: set[str] = set()
    # python>=3.12 needed for Path.walk()
    for node in maven_repo.rglob("*"):
        rel_node = str(node.relative_to(maven_repo))
        if node.is_dir():
            bs_dirs.add(rel_node)
        elif node.suffix == ".jar":
            bs_jars.add(rel_node)

    # What we built, and nothing more, should be in the backstage
    assert bs_dirs == {
        "org",
        "org/starcraft",
        "org/starcraft/top",
        "org/starcraft/top/1.0.0",
        "org/starcraft/submod",
        "org/starcraft/submod/1.0.0",
        "org/starcraft/subsubmod",
        "org/starcraft/subsubmod/1.0.0",
    }
    assert bs_jars == {"org/starcraft/subsubmod/1.0.0/subsubmod-1.0.0.jar"}


@pytest.fixture
def prepare_binaries(new_dir, partitions, monkeypatch):
    """Run a project that builds a set of Maven artifacts."""

    def run(target_dir):
        project_dir = Path(new_dir) / "binaries_source"
        shutil.copytree(SOURCE_DIR / "from_binaries/binaries_source", project_dir)
        monkeypatch.chdir(project_dir)
        work_dir = Path(new_dir / "binaries_source_work")
        parts_yaml = (project_dir / "parts.yaml").read_text()
        parts = yaml.safe_load(parts_yaml)

        lf = LifecycleManager(
            parts,
            application_name="binaries_source",
            cache_dir=new_dir,
            work_dir=work_dir,
            partitions=partitions,
        )
        actions = lf.plan(Step.BUILD)

        with lf.action_executor() as ctx:
            ctx.execute(actions)

        # Copy the generated/deployed artifacts to the location of the project where they
        # will be consumed in a new lifecycle.
        parts_dir = lf.project_info.parts_dir
        for dep in ("java-dep-add", "java-dep-print-addition"):
            # Copy the part's "export" dir, which contains the deployed artifact, to
            # the new project's source dir
            export_dir = parts_dir / dep / "export"
            assert export_dir.is_dir()
            target_dep_dir = target_dir / dep
            shutil.copytree(export_dir, target_dep_dir)

            # Remove the checksum files, because the original poms will need to be
            # fixed in the new project
            for digest in ("md5", "sha1"):
                for name in target_dir.glob(f"**/*.{digest}"):
                    name.unlink()

    return run


def test_maven_use_from_binaries(new_dir, partitions, monkeypatch, prepare_binaries):
    """Test the maven-use plugin when consuming directly from binaries.

    The test runs two lifecycles: the first one, called in ``prepare_binaries()``,
    builds Maven artifacts for two Java projects, which are then used as dependencies
    in the second lifecycle.
    """
    project_dir = Path(new_dir) / "binaries_consume"
    shutil.copytree(SOURCE_DIR / "from_binaries/binaries_consume", project_dir)

    prepare_binaries(project_dir)

    monkeypatch.chdir(project_dir)
    work_dir = Path(new_dir / "binaries_consume_work")
    parts_yaml = (project_dir / "parts.yaml").read_text()
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts,
        application_name="binaries_consume",
        cache_dir=new_dir,
        work_dir=work_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    jar = lf.project_info.prime_dir / "jar/hello-world-0.1.0.jar"
    output = subprocess.check_output(["java", "-jar", str(jar)], text=True)
    assert output == "1 plus 1 equals 2\n"
