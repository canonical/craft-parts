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
from typing import Literal, cast

from typing_extensions import override

from . import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)

RUBY_PREFIX = "/usr"
GEM_PREFIX = "/var/lib/gems/all"

# NOTE: To update ruby-install version, go to https://github.com/postmodern/ruby-install/tags
RUBY_INSTALL_VERSION = "0.10.1"

# NOTE: To update SHA256 checksum, run the following command (with updated version) and copy the output (one line) here:
#   curl -L https://github.com/postmodern/ruby-install/archive/refs/tags/v0.10.1.tar.gz -o ruby-install.tar.gz && sha256sum --tag ruby-install.tar.gz
RUBY_INSTALL_CHECKSUM = "SHA256 (ruby-install.tar.gz) = af09889b55865fc2a04e337fb4fe5632e365c0dce871556c22dfee7059c47a33"


class RubyFlavor(str, Enum):
    """All Ruby implementations supported by ruby-install."""

    ruby = "ruby"
    jruby = "jruby"
    truffleruby = "truffleruby"
    mruby = "mruby"


class RubyPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Ruby plugin."""

    plugin: Literal["ruby"] = "ruby"
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    ruby_gems: list[str] = []
    ruby_use_bundler: bool = False

    # build arguments
    ruby_flavor: RubyFlavor | None = None
    ruby_version: str | None = None
    ruby_use_jemalloc: bool = False
    ruby_shared: bool = False
    ruby_configure_options: list[str] = []


class RubyPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Ruby plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build Ruby applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        options = cast(RubyPluginProperties, self._options)
        has_ruby_deps = "ruby-deps" in (part_dependencies or [])
        if options.ruby_flavor or options.ruby_version:
            if None in (options.ruby_flavor, options.ruby_version):
                raise validator.errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="ruby-version and ruby-flavor must both be specified",
                )

            if has_ruby_deps:
                raise validator.errors.PluginEnvironmentValidationError(
                    part_name=self._part_name,
                    reason="ruby-deps cannot be used "
                    "when ruby-flavor and ruby-version are also specified",
                )
        elif not has_ruby_deps:
            # Not building Ruby -- everything should already be present
            for dependency in ["gem", "ruby"]:
                self.validate_dependency(
                    dependency=dependency,
                    plugin_name="ruby",
                    part_dependencies=part_dependencies,
                )


class RubyPlugin(Plugin):
    """A plugin for Ruby based projects.

    The desired Ruby interpreter is compiled using ruby-install.

    The ruby plugin uses the  following ruby-specific keywords:

    - ``ruby-flavor``
      (string)
      ruby,jruby,truffleruby,mruby
    - ``ruby-gems``
      (list of str)
      Defaults to []
    - ``ruby-version``
      (str)
      Minor version number of the specified interpreter flavor.
      e.g. '3.2', meaning the newest release of the 3.2.x series.
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
    validator_class = RubyPluginEnvironmentValidator
    _options: RubyPluginProperties

    def _should_build_ruby(self) -> bool:
        # Skip if user specified 'after: [ruby-deps]' in yaml
        return (
            self._options.ruby_flavor is not None
            and self._options.ruby_version is not None
        ) and "ruby-deps" not in self._part_info.part_dependencies

    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        packages: set[str] = set()

        if self._should_build_ruby():
            # curl: for fetching ruby-install itself
            # other packages: minimum necessary for mruby flavor
            # https://github.com/postmodern/ruby-install/blob/master/share/ruby-install/mruby/dependencies.sh
            packages |= {"curl", "build-essential", "bison"}

            if self._options.ruby_flavor != RubyFlavor.mruby:
                # package dependencies for standard ruby interpreter
                # https://github.com/postmodern/ruby-install/blob/master/share/ruby-install/ruby/dependencies.sh
                packages |= {
                    "xz-utils",
                    "zlib1g-dev",
                    "libyaml-dev",
                    "libssl-dev",
                    "libncurses-dev",
                    "libffi-dev",
                    "libreadline-dev",
                    "libjemalloc-dev",
                }

        return packages

    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        env = {
            # Where to find ruby and gem binaries
            # Prioritize staged executables
            "PATH": (
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/bin:"
                f"${{CRAFT_PART_INSTALL}}{GEM_PREFIX}/bin:"
                f"${{CRAFT_STAGE}}{RUBY_PREFIX}/bin:"
                f"${{CRAFT_STAGE}}{GEM_PREFIX}/bin:"
                f"${{PATH}}"
            ),
            # Where to find libruby.so
            "LD_LIBRARY_PATH": (
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/lib/${{CRAFT_ARCH_TRIPLET}}:"
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/lib:"
                f"${{CRAFT_STAGE}}{RUBY_PREFIX}/lib/${{CRAFT_ARCH_TRIPLET}}:"
                f"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"
            ),
            # Where to find ruby standard library (both native and interpreted)
            "RUBYLIB": (
                f"${{CRAFT_STAGE}}{RUBY_PREFIX}/lib/${{CRAFT_ARCH_TRIPLET}}/ruby/3.2.0/:"
                f"${{CRAFT_STAGE}}{RUBY_PREFIX}/lib/ruby/3.2.0/:"
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/lib/${{CRAFT_ARCH_TRIPLET}}/ruby/3.2.0/:"
                f"${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/lib/ruby/3.2.0/"
            ),
            # Where to look for installed gems
            "GEM_PATH": f"${{CRAFT_PART_INSTALL}}{GEM_PREFIX}",
            # Where to install new gems
            "GEM_HOME": f"${{CRAFT_PART_INSTALL}}{GEM_PREFIX}",
            # Tell "bundle install" to use same path as "gem install"
            "BUNDLE_PATH__SYSTEM": "true",
        }

        # mruby shouldn't care about gems at all, but the installer
        # fails to symlink with the GEM_HOME value above for some reason
        if self._options.ruby_flavor == RubyFlavor.mruby:
            env["GEM_HOME"] = "${CRAFT_PART_INSTALL}"

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
            flavor_str = cast(RubyFlavor, self._options.ruby_flavor).value

            # only for mruby: Install the rake gem into our custom GEM_HOME
            if self._options.ruby_flavor == RubyFlavor.mruby:
                commands.append("gem install --env-shebang --no-document rake")

            # NOTE: Use ruby-install to download, compile, and install Ruby
            commands.append("tar xfz ruby-install.tar.gz")
            commands.append(
                f"ruby-install-{RUBY_INSTALL_VERSION}/bin/ruby-install"
                f" --src-dir ${{CRAFT_PART_SRC}}"
                f" --install-dir ${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}"
                f" --no-install-deps --jobs=${{CRAFT_PARALLEL_BUILD_COUNT}}"
                f" {flavor_str}-{self._options.ruby_version}"
                f" -- {configure_opts}"
            )

        if self._options.ruby_use_bundler:
            # NOTE: Update bundler and avoid conflicts/prompts about replacing bundler
            #       executables by removing them first.
            commands.append(
                f"rm -f ${{CRAFT_PART_INSTALL}}{RUBY_PREFIX}/bin/{{bundle,bundler}}"
            )
            commands.append("gem install --env-shebang --no-document bundler")

            commands.append("bundle install --standalone")

            # If the source dir itself defines a gem, install it too
            # (`bundle install``only installs dependencies)
            for gemspec in self._part_info.part_src_dir.glob("*.gemspec"):
                commands.append(f"gem build {gemspec} --output {gemspec}.gem")
                commands.append(
                    f"gem install --env-shebang --no-document {gemspec}.gem"
                )

        if self._options.ruby_gems:
            commands.append(
                "gem install --env-shebang --no-document {}".format(
                    " ".join(self._options.ruby_gems)
                )
            )

        return commands
