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


def test_ruby_plugin_default(new_dir, partitions):
    """Plugin should use (but not stage) available Ruby interpreter."""
    source_location = Path(__file__).parent / "test_ruby"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: ruby
            source: {source_location}
            ruby-gems:
              # external dependency that installs an executable
              - rackup
            ruby-use-bundler: true
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_ruby", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    # ruby interpreter NOT explicitly staged
    interpreter = Path(lf.project_info.prime_dir, "usr", "bin", "ruby")
    assert not interpreter.exists()

    # from gem install
    rake_bin = Path(lf.project_info.prime_dir, "bin", "rackup")
    assert rake_bin.exists()

    # from bundle install
    ruby_root = Path(lf.project_info.prime_dir, "ruby")
    # e.g. "3.2.0"; will vary based on version in archive
    version_dir = next(ruby_root.iterdir())
    primed_script = version_dir / "bin" / "mytest"
    assert primed_script.exists()


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
    rackup_bin = Path(lf.project_info.prime_dir, "bin", "rackup")
    assert rackup_bin.exists()

    # from bundle install
    ruby_root = Path(lf.project_info.prime_dir, "ruby")
    # e.g. "3.2.0"; will vary based on version in archive
    version_dir = next(ruby_root.iterdir())
    primed_script = version_dir / "bin" / "mytest"
    assert primed_script.exists()


@pytest.mark.slow
def test_ruby_custom_flavor(new_dir, partitions):
    """Plugin should build the specified version of Ruby."""
    source_location = Path(__file__).parent / "test_ruby"

    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: ruby
            ruby-flavor: mruby
            ruby-version: "3.4.0"
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
    assert interpreter_version.startswith("mruby 3.4.0")


@pytest.mark.slow
def test_ruby_self_contained(new_dir, partitions):
    """Build a simple dependency tree of gems in self-contained mode."""
    source_location = Path(__file__).parent / "test_ruby"

    # mytest depends on specific version of rackup gem
    # rackup depends on rack and webrick gems
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          webrick:
            plugin: ruby
            source: https://github.com/ruby/webrick.git
            source-depth: 1
            ruby-self-contained: true
          rack:
            plugin: ruby
            source: https://github.com/rack/rack.git
            source-depth: 1
            source-tag: v3.2.1  # should match version check below
            ruby-self-contained: true
          rackup:
            plugin: ruby
            source: https://github.com/rack/rackup.git
            source-depth: 1
            source-tag: v2.0.0  # should match ./test_ruby/Gemfile
            ruby-self-contained: true
            after:
              - rack
              - webrick
          mytest:
            plugin: ruby
            source: {source_location}
            ruby-use-bundler: true
            ruby-self-contained: true
            after:
              - rackup
        """
    )
    parts = yaml.safe_load(parts_yaml)

    lf = LifecycleManager(
        parts, application_name="test_ruby", cache_dir=new_dir, partitions=partitions
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    ruby_root = Path(lf.project_info.prime_dir, "ruby")
    # e.g. "3.2.0"; will vary based on version in archive
    version_dir = next(ruby_root.iterdir())
    rackup_path = version_dir / "bin" / "rackup"
    rackup_version = subprocess.check_output(
        [rackup_path, "--version"], text=True,
        env={"GEM_PATH": version_dir},
    )
    # installed rackup executable should match gem version
    assert rackup_version.strip() == "Rack 3.2.1"
