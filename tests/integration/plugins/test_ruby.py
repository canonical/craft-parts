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


def have_ruby_2():
    # jammy was the first LTS release to have Ruby 3.0 in the archive
    try:
        return subprocess.check_output(
            ["ruby", "-e", "puts RUBY_VERSION"], text=True
        ).startswith("2")
    except subprocess.CalledProcessError:
        return False


@pytest.mark.skipif(
    have_ruby_2(), reason="Need Ruby 3.0+ to install Bundler from rubygems."
)
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
    ruby_prefix = Path(lf.project_info.prime_dir, "usr")
    interpreter = ruby_prefix / "bin" / "ruby"
    assert not interpreter.exists()

    # from gem install
    gem_prefix = Path(lf.project_info.prime_dir, "var", "lib", "gems", "all")
    rackup_bin = gem_prefix / "bin" / "rackup"
    assert rackup_bin.exists()
    assert subprocess.check_output(
        [rackup_bin, "--version"], text=True, env={"GEM_PATH": gem_prefix}
    ).startswith("Rack ")

    # from bundle install
    mytest_bin = gem_prefix / "bin" / "mytest"
    assert mytest_bin.exists()
    assert (
        subprocess.check_output(
            [mytest_bin], text=True, env={"GEM_PATH": gem_prefix}
        ).strip()
        == "it works!"
    )


@pytest.mark.skipif(
    have_ruby_2(), reason="Need Ruby 3.0+ to install Bundler from rubygems."
)
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
            override-build: |
              # To generalize this test case across multiple Ubuntu bases
              # with differing packaged Ruby versions, use a wildcard to
              # capture the versioned directory (e.g., 3.2.0, 3.3.0) and link
              # a static alias to it to be used as a fixed value for RUBYLIB.
              craftctl default
              cd $CRAFT_PART_INSTALL/usr/lib/ruby/
              export RUBY_ABI_VERSION=$(find . -maxdepth 1 -type d -name '*.*.*' | head -n 1)
              ln -s $RUBY_ABI_VERSION current
              cd ../$CRAFT_ARCH_TRIPLET/ruby/
              ln -s $RUBY_ABI_VERSION current

          foo:
            plugin: ruby
            source: {source_location}
            ruby-gems:
              # external dependency that installs an executable
              - rackup
            build-environment:
              - RUBYLIB: "$CRAFT_STAGE/usr/lib/ruby/current:$CRAFT_STAGE/usr/lib/$CRAFT_ARCH_TRIPLET/ruby/current"
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

    # Construct expected locations of installed files
    ruby_prefix = Path(lf.project_info.prime_dir, "usr")
    gem_prefix = Path(lf.project_info.prime_dir, "var", "lib", "gems", "all")
    env = {
        # Where to find ruby interpreter
        "PATH": ruby_prefix / "bin",
        # Where to find libruby.so
        "LD_LIBRARY_PATH": ruby_prefix / "lib" / lf.project_info.arch_triplet,
        # Where to find ruby standard library (both native and interpreted)
        "RUBYLIB": ":".join(
            [
                str(
                    ruby_prefix
                    / "lib"
                    / lf.project_info.arch_triplet
                    / "ruby"
                    / "current"
                ),
                str(ruby_prefix / "lib" / "ruby" / "current"),
            ]
        ),
        # Where to find installed gems
        "GEM_PATH": gem_prefix,
    }

    # from ruby-deps stage-packages
    interpreter = ruby_prefix / "bin" / "ruby"
    assert interpreter.exists()

    # from gem install
    rackup_bin = gem_prefix / "bin" / "rackup"
    assert rackup_bin.exists()
    assert subprocess.check_output(
        [rackup_bin, "--version"], text=True, env=env
    ).startswith("Rack ")

    # from bundle install
    mytest_bin = gem_prefix / "bin" / "mytest"
    assert mytest_bin.exists()
    assert (
        subprocess.check_output([mytest_bin], text=True, env=env).strip() == "it works!"
    )


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
