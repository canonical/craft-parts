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


@pytest.fixture
def meson():
    subprocess.run(["pip", "install", "meson"], check=True)
    yield
    subprocess.run(["pip", "uninstall", "meson", "--yes"], check=True)


@pytest.mark.usefixtures("mocker")
@pytest.mark.usefixtures("meson")
def test_meson_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: meson
            source: .
            meson-parameters:
              - --prefix=/
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("meson.build").write_text(
        textwrap.dedent(
            """\
            project('meson-hello', 'c')
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

    # ninja is installed in the ci test setup
    lf = LifecycleManager(
        parts, application_name="test_go", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"


@pytest.mark.usefixtures("mocker")
@pytest.mark.usefixtures("meson")
def test_meson_plugin_with_subdir(new_dir, partitions):
    """Verify meson builds with a source subdirectory."""
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: meson
            source: .
            source-subdir: test-subdir
            meson-parameters:
              - --prefix=/
        """
    )
    parts = yaml.safe_load(parts_yaml)

    source_subdir = Path("test-subdir")
    source_subdir.mkdir(parents=True)

    (source_subdir / "meson.build").write_text(
        textwrap.dedent(
            """\
            project('meson-hello', 'c')
            executable('hello', 'hello.c', install : true)
            """
        )
    )

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

    # ninja is installed in the ci test setup
    lf = LifecycleManager(
        parts, application_name="test_go", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "hello world\n"
