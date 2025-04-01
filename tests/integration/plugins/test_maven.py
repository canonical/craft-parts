# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
def use_mvnw(request):
    if request.param:
        yield request.param
        return
    source_location = Path(__file__).parent / "test_maven"
    mvnw_file = source_location / "mvnw"
    mvnw_file = mvnw_file.rename(f"{source_location}/mvnw.backup")
    yield request.param
    mvnw_file.rename(f"{source_location}/mvnw")


@pytest.mark.parametrize(
    ("use_mvnw", "stage_packages"),
    [(True, "[default-jre-headless]"), (False, "[default-jre-headless, maven]")],
    indirect=["use_mvnw"],
)
def test_maven_plugin(new_dir, partitions, use_mvnw, stage_packages):
    source_location = Path(__file__).parent / "test_maven"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {source_location}
            stage-packages: {stage_packages}
            maven-use-mvnw: {use_mvnw}
        """
    )
    parts = yaml.safe_load(parts_yaml)
    _run_maven_test(new_dir=new_dir, partitions=partitions, parts=parts)


@pytest.mark.parametrize("use_mvnw", [False], indirect=True)
def test_maven_plugin_use_maven_wrapper_wrapper_missing(
    capsys, new_dir, partitions, use_mvnw
):
    source_location = Path(__file__).parent / "test_maven"
    (source_location / "mvnw").unlink(missing_ok=True)

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {source_location}
            stage-packages: [default-jre-headless]
            maven-use-mvnw: True
        """
    )
    parts = yaml.safe_load(parts_yaml)
    with pytest.raises(errors.PluginBuildError) as exc:
        _run_maven_test(new_dir=new_dir, partitions=partitions, parts=parts)

    assert "Failed to run the build script for part 'foo'" in exc.value.brief
    assert (
        "mvnw file not found, refer to plugin documentation" in capsys.readouterr().err
    )


def _run_maven_test(new_dir, partitions, parts):
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

    prime_dir = lf.project_info.prime_dir
    java_binary = Path(prime_dir, "bin", "java")
    assert java_binary.is_file()

    output = subprocess.check_output(
        [str(java_binary), "-jar", f"{prime_dir}/jar/HelloWorld-1.0.jar"], text=True
    )
    assert output.strip() == "Hello from Maven-built Java"
