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

import logging
from typing import Any, Dict, List, Optional, Set, cast

from craft_parts import errors

from . import validator
from .base import Plugin, PluginModel, extract_plugin_properties
from .properties import PluginProperties

logger = logging.getLogger(__name__)


class RubyPluginProperties(PluginProperties, PluginModel):
    """The part properties used by the Ruby plugin."""

    ruby_flavor: str = 'ruby'
    ruby_version: str = '3.0'
    ruby_prefix: str = '/usr'
    ruby_use_jemalloc: bool = False
    ruby_shared: bool = False
    ruby_configure_options: List[str] = []

    source: str

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]):
        """Populate make properties from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = extract_plugin_properties(
            data, plugin_name="ruby", required=["source"]
        )
        return cls(**plugin_data)


class RubyPlugin(Plugin):
    """A plugin for Ruby based projects.

    The desired Ruby interpreter is compiled using ruby-install.

    The ruby plugin uses the common plugin keywords, plus the following ruby-
    specific keywords:

    - ``ruby-flavor``
      (string)
      ruby,jruby,rbx,truffleruby,mruby
    - ``ruby-version``
      (str)
      Defaults to '3.0', meaning the newest release of the 3.0.x series.
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
    """

    properties_class = RubyPluginProperties

    def get_build_snaps(self) -> Set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    def get_build_packages(self) -> Set[str]:
        packages = {"curl"}

        if options.ruby_use_jemalloc:
            packages.add("libjemalloc-dev")

        return packages

    def get_build_environment(self) -> Dict[str, str]:
        env = {
            "PATH": f"${{CRAFT_PART_INSTALL}}{self.options.ruby_prefix}/bin:${{PATH}}",
        }

        if options.ruby_shared:
            # for finding ruby.so when running `gem` or `bundle`
            env["LD_LIBRARY_PATH"] = f"${{CRAFT_PART_INSTALL}}{options.ruby_prefix}/lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"

        return env


    def _configure_opts(self) -> List[str]:
        configure_opts = [
            "--without-baseruby",
            "--enable-load-relative",
            "--disable-install-doc",
        ] + options.ruby_configure_options

        if options.ruby_shared:
            configure_opts.append("--enable-shared")
        if options.ruby_use_jemalloc:
            configure_opts.append("--with-jemalloc")

        return configure_opts


    def get_build_commands(self) -> List[str]:
        # NOTE: To update ruby-install version, go to https://github.com/postmodern/ruby-install/tags
        ruby_install_version = '0.8.5'

        # NOTE: To update SHA256 checksum, run the following command (with updated version) and copy the output (one line) here:
        #   curl -L https://github.com/postmodern/ruby-install/archive/refs/tags/v0.8.5.tar.gz -o ruby-install.tar.gz && sha256sum --tag ruby-install.tar.gz
        ruby_install_checksum = 'SHA256 (ruby-install.tar.gz) = 793fcf44dce375c6c191003c3bfd22ebc85fa296d751808ab315872f5ee0179b'

        configure_opts = ' '.join(_configure_opts())
        commands = ['uname -a', 'env']

        # NOTE: Download and verify ruby-install and use it to download, compile, and install Ruby
        commands.append(f"curl -L --proto '=https' --tlsv1.2 https://github.com/postmodern/ruby-install/archive/refs/tags/v{ruby_install_version}.tar.gz -o ruby-install.tar.gz")
        commands.append("echo 'Checksum of downloaded file:'")
        commands.append("sha256sum --tag ruby-install.tar.gz")
        commands.append("echo 'Checksum is correct if it matches:'")
        commands.append(f"echo '{ruby_install_checksum}'")
        commands.append(f"echo '{ruby_install_checksum}' | sha256sum --check --strict")
        commands.append("tar xfz ruby-install.tar.gz")
        commands.append(f"ruby-install-{ruby_install_version}/bin/ruby-install --src-dir ${{CRAFT_PART_SRC}} --install-dir ${{CRAFT_PART_INSTALL}}{options.ruby_prefix} --package-manager apt --jobs=${{CRAFT_PARALLEL_BUILD_COUNT}} {options.ruby_flavor}-{options.ruby_version} -- {configure_opts}")

        # NOTE: Update bundler and avoid conflicts/prompts about replacing bundler
        #       executables by removing them first.
        commands.append(f"rm -f ${{CRAFT_PART_INSTALL}}{options.ruby_prefix}/bin/{{bundle,bundler}}")
        commands.append("gem install --env-shebang --no-document bundler")

        if options.ruby_use_bundler:
            commands.append("bundle")

        if options.ruby_gems:
            commands.append("gem install --env-shebang --no-document {}".format(' '.join(options.ruby_gems)))

        return commands
