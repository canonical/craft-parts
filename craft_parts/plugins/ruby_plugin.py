# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

"""The Ruby plugin."""

import logging
from enum import Enum
from typing import Literal

from typing_extensions import override

from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)

RUBY_PREFIX = "/usr"

# NOTE: To update ruby-install version, go to https://github.com/postmodern/ruby-install/tags
RUBY_INSTALL_VERSION = "0.10.1"

# NOTE: To update SHA256 checksum, run the following command (with updated version) and copy the output (one line) here:
#   curl -L https://github.com/postmodern/ruby-install/archive/refs/tags/v0.10.1.tar.gz -o ruby-install.tar.gz && sha256sum --tag ruby-install.tar.gz
RUBY_INSTALL_CHECKSUM = "SHA256 (ruby-install.tar.gz) = af09889b55865fc2a04e337fb4fe5632e365c0dce871556c22dfee7059c47a33"


class RubyFlavor(str, Enum):
    """All Ruby implementations supported by ruby-install."""

    ruby = "ruby"
    jruby = "jruby"
    rbx = "rbx"
    truffleruby = "truffleruby"
    mruby = "mruby"


class RubyPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Ruby plugin."""

    plugin: Literal["ruby"] = "ruby"
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    ruby_gems: list[str] = []
    ruby_use_bundler: bool = False

    # build arguments
    ruby_flavor: RubyFlavor = RubyFlavor.ruby
    ruby_version: str = "3.2"
    ruby_use_jemalloc: bool = False
    ruby_shared: bool = False
    ruby_configure_options: list[str] = []


class RubyPlugin(Plugin):
    """A plugin for Ruby based projects.

    The desired Ruby interpreter is compiled using ruby-install.

    The ruby plugin uses the  following ruby-specific keywords:

    - ``ruby-flavor``
      (string)
      ruby,jruby,rbx,truffleruby,mruby
    - ``ruby-gems``
      (list of str)
      Defaults to []
    - ``ruby-version``
      (str)
      Defaults to '3.2', meaning the newest release of the 3.2.x series.
    - ``ruby-use-jemalloc``
      (bool)
      Defaults to False
    - ``ruby-shared``
      (bool)
      Defaults to False
    - ``ruby-configure-options``
      (list of str)
      Defaults to []
    - ``ruby-use-bundler``
      (bool)
      Defaults to False
    """

    properties_class = RubyPluginProperties
    _options: RubyPluginProperties

    def _should_build_ruby(self) -> bool:
        # Skip if user specified 'after: [ruby-deps]' in yaml
        return "ruby-deps" not in self._part_info.part_dependencies

    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        packages: set[str] = set()
        if self._should_build_ruby():
            # libssl-dev: to enable compiled binaries to fetch gems over HTTPS
            # curl: for fetching ruby-install itself
            packages |= {"curl", "libssl-dev"}
        return packages

    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        env = {
            "PATH": f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/bin:${{PATH}}",
            "GEM_HOME": "${CRAFT_PART_INSTALL}",
            "GEM_PATH": "${CRAFT_PART_INSTALL}",
            # some Ruby build scripts use bash syntax
            #"SHELL": "/bin/bash",
            #"MAKEOVERRIDES": "SHELL=/bin/bash",
        }

        if self._options.ruby_shared:
            # for finding ruby.so when running `gem` or `bundle`
            env["LD_LIBRARY_PATH"] = (
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"
            )

        return env

    def _configure_opts(self) -> list[str]:
        configure_opts = [
            "--without-baseruby",
            "--enable-load-relative",
            "--disable-install-doc",
            *self._options.ruby_configure_options,
        ]

        if self._options.ruby_shared:
            configure_opts.append("--enable-shared")
        if self._options.ruby_use_jemalloc:
            configure_opts.append("--with-jemalloc")

        return configure_opts

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to run during the pull step."""
        commands: list[str] = []

        if self._should_build_ruby():
            # NOTE: Download and verify ruby-install tool (to be executed during build phase)
            commands.append(
                f"curl -L --proto '=https' --tlsv1.2 https://github.com/postmodern/ruby-install/archive/refs/tags/v{RUBY_INSTALL_VERSION}.tar.gz -o ruby-install.tar.gz"
            )
            commands.append("echo 'Checksum of downloaded file:'")
            commands.append("sha256sum --tag ruby-install.tar.gz")
            commands.append("echo 'Checksum is correct if it matches:'")
            commands.append(f"echo '{RUBY_INSTALL_CHECKSUM}'")
            commands.append(
                f"echo '{RUBY_INSTALL_CHECKSUM}' | sha256sum --check --strict"
            )

        return commands

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        configure_opts = " ".join(self._configure_opts())
        commands = ["uname -a", "env"]

        if self._should_build_ruby():
            # NOTE: Use ruby-install to download, compile, and install Ruby
            commands.append("tar xfz ruby-install.tar.gz")
            commands.append(
                f"ruby-install-{RUBY_INSTALL_VERSION}/bin/ruby-install"
                f" --src-dir ${{CRAFT_PART_SRC}}"
                f" --install-dir ${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}"
                f" --package-manager apt --jobs=${{CRAFT_PARALLEL_BUILD_COUNT}}"
                f" {self._options.ruby_flavor.value}-{self._options.ruby_version}"
                f" -- {configure_opts}"
            )

        if self._options.ruby_use_bundler:
            # NOTE: Update bundler and avoid conflicts/prompts about replacing bundler
            #       executables by removing them first.
            commands.append(
                f"rm -f ${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/bin/{{bundle,bundler}}"
            )
            commands.append("gem install --env-shebang --no-document bundler")
            commands.append("bundle config path ${CRAFT_PART_INSTALL}")
            commands.append("bundle")

        if self._options.ruby_gems:
            commands.append(
                "gem install --env-shebang --no-document {}".format(
                    " ".join(self._options.ruby_gems)
                )
            )

        return commands
