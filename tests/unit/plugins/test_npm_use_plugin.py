# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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

import pytest
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.parts import Part
from craft_parts.plugins.npm_use_plugin import NpmUsePlugin

# pylint: disable=too-many-public-methods


@pytest.fixture
def part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {}),
    )


@pytest.fixture
def self_contained_part_info(new_dir):
    return PartInfo(
        project_info=ProjectInfo(application_name="test", cache_dir=new_dir),
        part=Part("my-part", {"build-attributes": ["self-contained"]}),
    )


@pytest.fixture
def mocker_deps(mocker):
    read_pkg = mocker.patch(
        "craft_parts.utils.npm_utils.read_pkg",
        return_value={"dependencies": {"my-dep": "^1.0.0"}},
    )
    find_tarballs = mocker.patch(
        "craft_parts.utils.npm_utils.find_tarballs",
        return_value=[("my-dep", "^1.0.0", ["1.0.0"])],
    )
    write_pkg = mocker.patch("craft_parts.utils.npm_utils.write_pkg")
    return read_pkg, find_tarballs, write_pkg


class TestPluginNpmUsePlugin:
    """Npm-Use plugin tests."""

    def test_get_build_commands(self, part_info):
        properties = NpmUsePlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmUsePlugin(properties=properties, part_info=part_info)

        assert plugin.get_build_commands() == [
            f'mv "$(npm pack . | tail -1)" "{part_info.part_export_dir}/npm-cache/"'
        ]

    def test_get_self_contained_build_commands(
        self, self_contained_part_info, mocker_deps
    ):
        _, _, write_pkg = mocker_deps
        properties = NpmUsePlugin.properties_class.unmarshal({"source": "."})
        plugin = NpmUsePlugin(properties=properties, part_info=self_contained_part_info)

        cmd = plugin.get_build_commands()

        assert "SEMVER_BIN" in cmd[0]
        assert cmd[1] == "TARBALLS="
        assert "'^1.0.0' 1.0.0" in cmd[2]

        cache_dir = self_contained_part_info.backstage_dir / "npm-cache"
        assert f'TARBALLS="$TARBALLS {cache_dir}/my-dep-$BEST_VERSION.tgz' in cmd[2]

        assert cmd[-3:] == [
            "npm install --offline --include=dev --no-package-lock $TARBALLS",
            f"cp {self_contained_part_info.part_build_subdir}/.parts/package.bundled.json package.json",
            f'mv "$(npm pack . | tail -1)" "{self_contained_part_info.part_export_dir}/npm-cache/"',
        ]

        write_pkg.assert_called_once()
        args, _ = write_pkg.call_args
        assert "bundledDependencies" in args[1]
        assert args[1]["bundledDependencies"] == ["my-dep"]
