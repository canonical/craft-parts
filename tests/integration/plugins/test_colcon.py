# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

pytestmark = [pytest.mark.plugin]


def test_colcon_plugin(new_dir, partitions):
    source_location = Path(__file__).parent / "test_colcon"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: colcon
            source: {source_location}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_colcon", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    package_python_primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert package_python_primed_script.exists()
    assert (
        package_python_primed_script.open().readline().rstrip() == "#!/usr/bin/python3"
    )

    package_cpp_primed_bin = Path(lf.project_info.prime_dir, "bin", "mytest_cpp")
    assert package_cpp_primed_bin.exists()
    output = subprocess.check_output([str(package_cpp_primed_bin)], text=True)
    assert output == "Hello from C++\n"

    output = subprocess.check_output(["file", str(package_cpp_primed_bin)], text=True)
    assert output.count("debug_info") == 0


def test_colcon_plugin_package_selection(new_dir, partitions):
    source_location = Path(__file__).parent / "test_colcon"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: colcon
            source: {source_location}
            colcon-packages: [package_python]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_colcon", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    package_python_primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert package_python_primed_script.exists()
    assert (
        package_python_primed_script.open().readline().rstrip() == "#!/usr/bin/python3"
    )

    package_cpp_primed_bin = Path(lf.project_info.prime_dir, "bin", "mytest_cpp")
    assert not package_cpp_primed_bin.exists()


def test_colcon_plugin_package_ignore(new_dir, partitions):
    source_location = Path(__file__).parent / "test_colcon"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: colcon
            source: {source_location}
            colcon-packages-ignore: [package_python]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_colcon", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    package_python_primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert not package_python_primed_script.exists()

    package_cpp_primed_bin = Path(lf.project_info.prime_dir, "bin", "mytest_cpp")
    assert package_cpp_primed_bin.exists()
    output = subprocess.check_output([str(package_cpp_primed_bin)], text=True)
    assert output == "Hello from C++\n"


def test_colcon_plugin_cmake_args(new_dir, partitions):
    source_location = Path(__file__).parent / "test_colcon"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: colcon
            source: {source_location}
            colcon-packages-ignore: [package_python]
            colcon-cmake-args: ["-DCMAKE_BUILD_TYPE=Debug"]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_colcon", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    package_python_primed_script = Path(lf.project_info.prime_dir, "bin", "mytest")
    assert not package_python_primed_script.exists()

    package_cpp_primed_bin = Path(lf.project_info.prime_dir, "bin", "mytest_cpp")
    assert package_cpp_primed_bin.exists()

    output = subprocess.check_output(["file", str(package_cpp_primed_bin)], text=True)
    assert output.count("debug_info") == 1
