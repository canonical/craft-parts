# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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

import os
import re
import subprocess
from pathlib import Path

import pytest
from craft_parts import ProjectDirs
from craft_parts.sources import errors, snap_source, sources

_LOCAL_DIR = Path(__file__).parent


class TestSnapSource:
    """Snap source pull tests."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._path = new_dir
        self._test_file = _LOCAL_DIR / "data" / "test-snap.snap"
        self._dest_dir = new_dir / "dest_dir"
        self._dest_dir.mkdir()
        self._dirs = ProjectDirs(partitions=partitions)
        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        ("param", "value"),
        [
            ("source_tag", "fake-tag"),
            ("source_branch", "fake-branch"),
            ("source_commit", "fake-commit"),
            ("source_depth", 1),
        ],
    )
    def test_invalid_parameter(self, new_dir, param, value):
        kwargs = {param: value}
        with pytest.raises(errors.InvalidSourceOption) as raised:
            sources.SnapSource(
                source="test.snap",
                part_src_dir=Path(),
                cache_dir=new_dir,
                project_dirs=self._dirs,
                **kwargs,
            )
        assert raised.value.option == param.replace("_", "-")

    def test_pull_snap_file_must_extract(self, new_dir):
        source = sources.SnapSource(
            str(self._test_file),
            self._dest_dir,
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )
        source.pull()

        assert Path(self._dest_dir / "meta.basic").is_dir()
        assert Path(self._dest_dir / "meta.basic/snap.yaml").is_file()

    def test_has_source_handler_entry(self):
        assert (
            sources._get_source_handler_class("", source_type="snap")
            is sources.SnapSource
        )

    def test_pull_failure_bad_unsquash(self, new_dir, mocker):
        mocker.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, [])
        )
        source = sources.SnapSource(
            str(self._test_file),
            self._dest_dir,
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )

        with pytest.raises(sources.errors.PullError) as raised:
            source.pull()

        assert re.match(
            f"unsquashfs -force -dest {self._path}/\\w+ "
            f"{self._path}/dest_dir/test-snap.snap",
            " ".join([str(s) for s in raised.value.command]),
        )
        assert raised.value.exit_code == 1


@pytest.mark.usefixtures("new_dir")
class TestGetName:
    """Checks for snap name retrieval from snap.yaml."""

    def test_get_name(self):
        os.mkdir("meta")

        with open(os.path.join("meta", "snap.yaml"), "w") as snap_yaml_file:
            print("name: my-snap", file=snap_yaml_file)
        assert snap_source._get_snap_name("snap", ".") == "my-snap"

    def test_no_name_yaml(self):
        os.mkdir("meta")

        with open(os.path.join("meta", "snap.yaml"), "w") as snap_yaml_file:
            print("summary: no name", file=snap_yaml_file)

        with pytest.raises(sources.errors.InvalidSnapPackage) as raised:
            snap_source._get_snap_name("snap", ".")
        assert raised.value.snap_file == "snap"

    def test_no_snap_yaml(self):
        os.mkdir("meta")

        with pytest.raises(sources.errors.InvalidSnapPackage) as raised:
            snap_source._get_snap_name("snap", ".")
        assert raised.value.snap_file == "snap"
