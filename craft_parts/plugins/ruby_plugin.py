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

"""The Ruby plugin."""

from enum import Enum
import logging
import subprocess
from typing import Dict, List, Literal, Set
from typing_extensions import override

from craft_parts.plugins import validator
from .base import Plugin
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class RubyFlavor(str, Enum):
    """Ruby interpreters supported by ruby-install"""
    ruby = "ruby"
    jruby = "jruby"
    rbx = "rbx"
    truffleruby = "truffleruby"
    mruby = "mruby"


class RubyPluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Ruby plugin."""

    plugin: Literal["ruby"] = "ruby"
    source: str  # pyright: ignore[reportGeneralTypeIssues]

    ruby_gems: List[str] = []
    ruby_use_bundler: bool = False

    # build arguments
    ruby_flavor: RubyFlavor = RubyFlavor.ruby
    ruby_version: str = '3.2'
    ruby_prefix: str = '/usr'
    ruby_use_jemalloc: bool = False
    ruby_shared: bool = False
    ruby_configure_options: List[str] = []


class RubyPluginEnvironmentValidator(validator.PluginEnvironmentValidator):
    """Check the execution environment for the Ruby plugin.

    :param part_name: The part whose build environment is being validated.
    :param env: A string containing the build step environment setup.
    """

    _options: RubyPluginProperties

    @override
    def validate_environment(
        self, *, part_dependencies: list[str] | None = None
    ) -> None:
        """Ensure the environment has the dependencies to build Ruby applications.

        :param part_dependencies: A list of the parts this part depends on.
        """
        if "ruby-deps" in (part_dependencies or ()):
            self.validate_dependency(
                dependency="ruby",
                plugin_name=self._options.plugin,
                part_dependencies=part_dependencies,
            )


class RubyPlugin(Plugin):
    """A plugin for Ruby based projects.

    The desired Ruby interpreter is compiled using ruby-install.

    The ruby plugin uses the common plugin keywords, plus the following ruby-
    specific keywords:

    - ``ruby-flavor``
      (string)
      ruby,jruby,rbx,truffleruby,mruby
    - ``ruby-gems``
      (list of str)
      Defaults to []
    - ``ruby-version``
      (str)
      Defaults to '3.2', meaning the newest release of the 3.2.x series.
    - ``ruby-prefix``
      (str)
      Defaults to '/usr'
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

    def _system_has_ruby(self) -> bool:
        try:
            ruby_version = subprocess.check_output(["ruby", "--version"], text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        return "ruby" in ruby_version

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        packages = {"curl"}

        if self._options.ruby_use_jemalloc:
            packages.add("libjemalloc-dev")

        return packages

    def get_build_environment(self) -> Dict[str, str]:
        env = {
            "PATH": f"${{CRAFT_PART_INSTALL}}{self._options.ruby_prefix}/bin:${{PATH}}",
            "GEM_HOME": str(self._part_info.part_install_dir),
            "GEM_PATH": str(self._part_info.part_install_dir),
        }

        if self._options.ruby_shared:
            # for finding ruby.so when running `gem` or `bundle`
            env["LD_LIBRARY_PATH"] = f"${{CRAFT_PART_INSTALL}}{self._options.ruby_prefix}/lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"

        return env


    def _configure_opts(self) -> List[str]:
        configure_opts = [
            "--without-baseruby",
            "--enable-load-relative",
            "--disable-install-doc",
        ] + self._options.ruby_configure_options

        if self._options.ruby_shared:
            configure_opts.append("--enable-shared")
        if self._options.ruby_use_jemalloc:
            configure_opts.append("--with-jemalloc")

        return configure_opts


    def get_build_commands(self) -> List[str]:
        configure_opts = ' '.join(self._configure_opts())
        commands = ['uname -a', 'env']
        install_dir =  self._part_info.part_install_dir

        # Install Ruby only if not already present, e.g. provided by another part
        if not self._system_has_ruby():
            # NOTE: To update ruby-install version, go to https://github.com/postmodern/ruby-install/tags
            ruby_install_version = '0.10.1'

            # NOTE: To update SHA256 checksum, run the following command (with updated version) and copy the output (one line) here:
            #   curl -L https://github.com/postmodern/ruby-install/archive/refs/tags/v0.10.1.tar.gz -o ruby-install.tar.gz && sha256sum --tag ruby-install.tar.gz
            ruby_install_checksum = 'SHA256 (ruby-install.tar.gz) = af09889b55865fc2a04e337fb4fe5632e365c0dce871556c22dfee7059c47a33'

            # NOTE: Download and verify ruby-install and use it to download, compile, and install Ruby
            commands.append(f"curl -L --proto '=https' --tlsv1.2 https://github.com/postmodern/ruby-install/archive/refs/tags/v{ruby_install_version}.tar.gz -o ruby-install.tar.gz")
            commands.append("echo 'Checksum of downloaded file:'")
            commands.append("sha256sum --tag ruby-install.tar.gz")
            commands.append("echo 'Checksum is correct if it matches:'")
            commands.append(f"echo '{ruby_install_checksum}'")
            commands.append(f"echo '{ruby_install_checksum}' | sha256sum --check --strict")
            commands.append("tar xfz ruby-install.tar.gz")
            commands.append(f"ruby-install-{ruby_install_version}/bin/ruby-install --src-dir ${{CRAFT_PART_SRC}} --install-dir ${{CRAFT_PART_INSTALL}}{self._options.ruby_prefix} --package-manager apt --jobs=${{CRAFT_PARALLEL_BUILD_COUNT}} {self._options.ruby_flavor}-{self._options.ruby_version} -- {configure_opts}")

        # NOTE: Update bundler and avoid conflicts/prompts about replacing bundler
        #       executables by removing them first.
        commands.append(f"rm -f ${{CRAFT_PART_INSTALL}}{self._options.ruby_prefix}/bin/{{bundle,bundler}}")
        commands.append(f"gem install --env-shebang --no-document --install-dir {install_dir} bundler")

        if self._options.ruby_use_bundler:
            commands.append(f"bundle config path {install_dir}")
            commands.append("bundle")

        if self._options.ruby_gems:
            commands.append("gem install --env-shebang --no-document {}".format(' '.join(self._options.ruby_gems)))

        return commands
