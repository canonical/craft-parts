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
"""Integration tests for parts that depend on each other."""


import os
import pathlib
from typing import cast

import craft_parts
import pytest
import yaml
from craft_parts import plugins
from craft_parts.plugins import cmake_plugin
from typing_extensions import override


class CMakeBackstagePlugin(cmake_plugin.CMakePlugin):

    @override
    def get_build_commands(self) -> list[str]:
        options = cast(cmake_plugin.CMakePluginProperties, self._options)
        return super().get_build_commands() + [
            f"mv {self._part_info.part_install_dir}/usr/include {self._part_info.part_export_dir}/include"
        ]


@pytest.mark.parametrize(
    "project",
    [
        "cargo-package",
    ]
)
def test_dependent_parts(new_path: pathlib.Path, project):
    """Test building pygit2 with a dependent part that builds libgit2."""
    plugins.register({"cmake": CMakeBackstagePlugin})
    parts_dir = pathlib.Path(__file__).parent / project
    backstage_dir = new_path / "backstage"
    parts = yaml.safe_load((parts_dir / "parts.yaml").read_text())


    lf = craft_parts.LifecycleManager(
        parts, application_name="test_dependent_parts", cache_dir=new_path,
        parallel_build_count=len(os.sched_getaffinity(0))
    )

    actions = lf.plan(craft_parts.Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert backstage_dir.is_dir()

    children = list(backstage_dir.rglob("*"))

    lf.clean(part_names=["root"])

    # TODO: Uncomment this when we have cleaning.
    # for child in children:
    #     assert not child.is_file()
