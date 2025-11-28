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

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [pytest.mark.plugin]


def test_ruby_deps_part(new_dir, partitions):
    """Plugin should use interpreter from ruby-deps part dependency."""
    source_location = Path(__file__).parent / "test_ruby"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          ruby-deps:
            plugin: nil
            stage-packages:
              # use Ruby deb packages from archive
              - ruby
              - ruby-bundler
          foo:
            plugin: ruby
            source: {source_location}
            ruby-gems:
              # external dependency that installs an executable
              - rackup
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

    # from ruby-deps stage-packages
    interpreter = Path(lf.project_info.prime_dir, "usr", "bin", "ruby")
    assert interpreter.exists()

    # from gem install
    rake_bin = Path(lf.project_info.prime_dir, "bin", "rackup")
    assert rake_bin.exists()

    # from bundle install
    ruby_root = Path(lf.project_info.prime_dir, "ruby")
    # e.g. "3.2.0"; will vary based on version in archive
    version_dir = next(ruby_root.iterdir())
    primed_script = version_dir / "bin" / "mytest"
    assert primed_script.exists()


@pytest.mark.slow
def test_ruby_custom_interpreter(new_dir, partitions):
    """Plugin should build the specified version of Ruby."""
    source_location = Path(__file__).parent / "test_ruby"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: ruby
            ruby-version: "3.4.7"
            ruby-configure-options:
              # limit extension set for faster build during test execution
              - "--with-ext=monitor"
              #- "--disable-rubygems"
            source: {source_location}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_ruby", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    interpreter_path = Path(lf.project_info.prime_dir, "usr", "bin", "ruby")
    interpreter_version = subprocess.check_output(
        [interpreter_path, "--version"], text=True
    )
    assert interpreter_version.startswith("ruby 3.4.7")
