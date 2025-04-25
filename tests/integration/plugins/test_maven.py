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

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, errors


@pytest.fixture
def testing_source_dir(new_dir):
    source_location = Path(__file__).parent / "test_maven"
    shutil.copytree(source_location, new_dir, dirs_exist_ok=True)
    return Path(new_dir)


@pytest.fixture
def use_maven_wrapper(request, testing_source_dir):
    if request.param:
        yield request.param
        return
    (testing_source_dir / "mvnw").unlink(missing_ok=True)
    yield request.param
    return


@pytest.mark.parametrize(
    ("use_maven_wrapper", "stage_packages"),
    [(True, "[default-jre-headless]"), (False, "[default-jre-headless, maven]")],
    indirect=["use_maven_wrapper"],
)
def test_maven_plugin(
    new_dir, testing_source_dir, partitions, use_maven_wrapper, stage_packages
):
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {testing_source_dir}
            stage-packages: {stage_packages}
            maven-use-wrapper: {use_maven_wrapper}
        """
    )
    parts = yaml.safe_load(parts_yaml)
    _run_maven_test(new_dir=new_dir, partitions=partitions, parts=parts)


@pytest.mark.parametrize("use_maven_wrapper", [False], indirect=True)
def test_maven_plugin_use_maven_wrapper_wrapper_missing(
    new_dir, partitions, testing_source_dir, use_maven_wrapper
):
    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {testing_source_dir}
            stage-packages: [default-jre-headless]
            maven-use-wrapper: True
        """
    )
    parts = yaml.safe_load(parts_yaml)
    with pytest.raises(errors.PluginBuildError) as exc:
        _run_maven_test(new_dir=new_dir, partitions=partitions, parts=parts)

    assert "Failed to run the build script for part 'foo'" in exc.value.brief


def _run_maven_test(new_dir, partitions, parts):
    lf = LifecycleManager(
        parts,
        application_name="test_maven",
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
