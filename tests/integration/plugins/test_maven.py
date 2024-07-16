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

import yaml
from craft_parts import LifecycleManager, Step


def test_maven_plugin(new_dir, partitions):
    source_location = Path(__file__).parent / "test_maven"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: maven
            source: {source_location}
            stage-packages: [default-jre-headless]
        """
    )
    parts = yaml.safe_load(parts_yaml)
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
