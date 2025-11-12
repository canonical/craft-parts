# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023-2025 Canonical Ltd.
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

import textwrap
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step


def test_ruby_deps_part(new_dir, partitions):
    """Plugin should skip building Ruby if another part named ruby-deps exists."""
    source_location = Path(__file__).parent / "test_ruby"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          ruby-deps:
            plugin: nil
            #build-packages:
            #  # use Ruby deb packages from archive
            #  - ruby-dev
            #  - ruby
            #stage-packages:
            #  - ruby
          foo:
            plugin: ruby
            source: {source_location}
            ruby-use-bundler: true
            after:
              - ruby-deps
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_ruby", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    primed_script = Path(lf.project_info.prime_dir, "ruby", "3.2.0", "bin", "mytest")
    assert primed_script.exists()
