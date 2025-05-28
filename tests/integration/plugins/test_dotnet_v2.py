# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step, plugins
from craft_parts.plugins import dotnet_v2_plugin
from overrides import override


def test_dotnet_plugin(new_dir, partitions):
    yaml_path = Path(__file__).parent / "test_dotnet_v2"
    with open(yaml_path / "parts.yaml") as file:
        parts = yaml.safe_load(file)
        parts['parts']['foo']['source'] = str(yaml_path)

    plugins.unregister("dotnet")
    plugins.register({"dotnet": dotnet_v2_plugin.DotnetV2Plugin})

    lf = LifecycleManager(
        parts, application_name="test_dotnet_v2", cache_dir=new_dir, partitions=partitions
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "dotnet")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "Hello, World!\n"


def test_dotnet_plugin_no_dotnet(new_dir, partitions, mocker):
    """Test the dotnet plugin while pretending dotnet isn't installed."""

    class FailSpecificCmdValidator(dotnet_v2_plugin.DotnetV2PluginEnvironmentValidator):
        """A validator that always fails the first time we run `dotnet --version`."""

        __already_run = False

        @override
        def _execute(self, cmd: str) -> str:
            if cmd == "dotnet --version" and not self.__already_run:
                self.__class__.__already_run = True
                raise subprocess.CalledProcessError(127, cmd)
            return super()._execute(cmd)

    mocker.patch.object(
        dotnet_v2_plugin.DotnetV2Plugin, "validator_class", FailSpecificCmdValidator
    )

    test_dotnet_plugin(new_dir, partitions)


def test_dotnet_plugin_fake_dotnet(new_dir, partitions, mocker):
    """Test the dotnet plugin while pretending dotnet is installed."""

    class AlwaysFindDotnetValidator(
        dotnet_v2_plugin.DotnetV2PluginEnvironmentValidator
    ):
        """A validator that always succeeds the first time running `dotnet --version`."""

        __already_run = False

        @override
        def _execute(self, cmd: str) -> str:
            if cmd != "dotnet --version":
                return super()._execute(cmd)
            try:
                return super()._execute(cmd)
            except subprocess.CalledProcessError:
                if self.__already_run:
                    raise
                return ""
            finally:
                self.__class__.__already_run = True

    mocker.patch.object(
        dotnet_v2_plugin.DotnetV2Plugin, "validator_class", AlwaysFindDotnetValidator
    )

    test_dotnet_plugin(new_dir, partitions)
