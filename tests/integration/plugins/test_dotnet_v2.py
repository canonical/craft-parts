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

import platform
import subprocess
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step, plugins
from craft_parts.infos import _get_host_architecture
from craft_parts.plugins import dotnet_v2_plugin

pytestmark = [
    pytest.mark.plugin,
    pytest.mark.skipif(
        _get_host_architecture() not in dotnet_v2_plugin._DEBIAN_ARCH_TO_DOTNET_RID,
        reason="No dotnet runtime for this architecture.",
    ),
    pytest.mark.skipif(
        platform.libc_ver()[1] < "2.34",
        reason="glibc too old. This plugin is only expected to work with jammy or later.",
    ),
]


def test_dotnet_plugin(new_dir, partitions):
    project_path = Path(__file__).parent / "test_dotnet_v2"
    with (project_path / "parts.yaml").open() as file:
        parts = yaml.safe_load(file)
        parts["parts"]["foo"]["source"] = str(project_path)

    plugins.unregister("dotnet")
    plugins.register({"dotnet": dotnet_v2_plugin.DotnetV2Plugin})

    lf = LifecycleManager(
        parts,
        application_name="test_dotnet_v2",
        cache_dir=new_dir,
        partitions=partitions,
    )

    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "dotnet")

    output = subprocess.check_output([str(binary)], text=True)
    assert output == "Hello, World!\n"


def test_dotnet_plugin_no_dotnet(new_dir, partitions, fp):
    """Test the dotnet plugin while pretending dotnet isn't installed."""
    fp.allow_unregistered(allow=True)
    fp.register_subprocess(["dotnet", "--version"], returncode=127)
    test_dotnet_plugin(new_dir, partitions)


def test_dotnet_plugin_fake_dotnet(new_dir, partitions, fp):
    """Test the dotnet plugin while pretending dotnet is installed."""
    fp.allow_unregistered(allow=True)
    # First call fails
    fp.register_subprocess(
        ["dotnet", "--version"],
        returncode=127,
    )
    # Second call succeeds
    fp.register_subprocess(
        ["dotnet", "--version"],
        stdout="6.0.0",
    )

    test_dotnet_plugin(new_dir, partitions)
