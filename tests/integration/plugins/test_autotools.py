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


def test_autotools_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """
        parts:
          hello:
            # Consuming the tarball instead of the "raw" source
            # removes coverage on testing autotools-bootstrap-parameters
            source: https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/hello/2.10-3build1/hello_2.10.orig.tar.gz
            plugin: autotools
            autotools-configure-parameters:
              - --prefix=/usr/
            build-packages:
              - git
              - gperf
              - help2man
              - texinfo
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_autotools",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    prime_dir = lf.project_info.prime_dir
    hello_binary = Path(prime_dir, "usr", "bin", "hello")
    assert hello_binary.is_file()

    output = subprocess.check_output([str(hello_binary)], text=True)
    assert output.strip() == "Hello, world!"
