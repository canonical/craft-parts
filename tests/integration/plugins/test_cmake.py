# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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


@pytest.mark.parametrize(
    ("prefix", "install_path"),
    [
        (None, "usr/local/bin"),
        ("", "bin"),
        ("/usr/local", "usr/local/bin"),
        ("/something/else", "something/else/bin"),
    ],
)
def test_cmake_plugin(new_dir, partitions, prefix, install_path):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: cmake
            source: .
        """
    )
    if prefix is not None:
        parts_yaml += f"    cmake-parameters: [-DCMAKE_INSTALL_PREFIX={prefix}]"

    parts = yaml.safe_load(parts_yaml)

    Path("cmake.build").write_text(
        textwrap.dedent(
            """\
            project('cmake-hello', 'c')
            executable('hello', 'hello.c', install : true)
            """
        )
    )

    Path("hello.c").write_text(
        textwrap.dedent(
            """\
            #include <stdio.h>

            int main()
            {
                printf(\"hello world\\n\");
                return 0;
            }
            """
        )
    )

    Path("CMakeLists.txt").write_text(
        textwrap.dedent(
            """\
            cmake_minimum_required(VERSION 2.6)
            project(cmake-hello C)
            add_executable(cmake-hello hello.c)
            install(TARGETS cmake-hello RUNTIME DESTINATION bin)
            """
        )
    )

    lf = LifecycleManager(
        parts, application_name="test_cmake", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, install_path, "cmake-hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


@pytest.mark.parametrize(
    ("prefix", "install_path"),
    [
        (None, "usr/local/bin"),
        ("", "bin"),
        ("/usr/local", "usr/local/bin"),
        ("/something/else", "something/else/bin"),
    ],
)
def test_cmake_plugin_subdir(new_dir, partitions, prefix, install_path):
    """Verify cmake builds with a source subdirectory."""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: cmake
            source: .
            source-subdir: test-subdir
        """
    )
    if prefix is not None:
        parts_yaml += f"    cmake-parameters: [-DCMAKE_INSTALL_PREFIX={prefix}]"

    parts = yaml.safe_load(parts_yaml)

    source_subdir = Path("test-subdir")
    source_subdir.mkdir(parents=True)

    (source_subdir / "hello.c").write_text(
        textwrap.dedent(
            """\
            #include <stdio.h>

            int main()
            {
                printf(\"hello world\\n\");
                return 0;
            }
            """
        )
    )

    (source_subdir / "CMakeLists.txt").write_text(
        textwrap.dedent(
            """\
            cmake_minimum_required(VERSION 2.6)
            project(cmake-hello C)
            add_executable(cmake-hello hello.c)
            install(TARGETS cmake-hello RUNTIME DESTINATION bin)
            """
        )
    )

    lf = LifecycleManager(
        parts, application_name="test_cmake", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, install_path, "cmake-hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"
