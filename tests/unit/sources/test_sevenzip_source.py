# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017 Tim Süberkrüb
# Copyright 2017-2022 Canonical Ltd.
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

import os.path
import shutil
import subprocess
from pathlib import Path
from unittest.mock import call

import pytest

from craft_parts.sources import sources


@pytest.fixture
def fake_7z_file(new_dir):
    name = "fake-7z-file.7z"
    Path(name).touch()
    return name


@pytest.fixture
def part_src_dir(new_dir):
    name = "part-src-dir"
    Path(name).mkdir()
    return name


class TestSevenZip:
    """Tests for the 7z source handler."""

    def test_pull_7z_file_must_extract(
        self, fake_7z_file, part_src_dir, new_dir, mocker
    ):
        check_output_mock = mocker.patch("subprocess.check_output")

        sevenzip = sources.SevenzipSource(fake_7z_file, part_src_dir, cache_dir=new_dir)
        sevenzip.pull()

        assert check_output_mock.mock_calls == [
            call(
                ["7z", "x", os.path.join(new_dir, part_src_dir, fake_7z_file)],
                text=True,
                cwd=part_src_dir,
            ),
            call().strip(),
        ]

    def test_extract_and_keep_7zfile(self, fake_7z_file, part_src_dir, new_dir, mocker):
        check_output_mock = mocker.patch("subprocess.check_output")

        sevenzip = sources.SevenzipSource(fake_7z_file, part_src_dir, cache_dir=new_dir)
        # This is the first step done by pull. We don't call pull to call the
        # second step with a different keep_7z value.
        shutil.copy2(sevenzip.source, sevenzip.part_src_dir)
        sevenzip.provision(dst=part_src_dir, keep=True)

        assert check_output_mock.mock_calls == [
            call(
                ["7z", "x", os.path.join(new_dir, part_src_dir, fake_7z_file)],
                text=True,
                cwd=part_src_dir,
            ),
            call().strip(),
        ]
        assert Path(fake_7z_file).exists()

    def test_pull_failure(self, fake_7z_file, part_src_dir, new_dir, mocker):
        check_output_mock = mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "error"),
        )
        sevenzip = sources.SevenzipSource(fake_7z_file, part_src_dir, cache_dir=new_dir)

        with pytest.raises(sources.errors.PullError) as raised:
            sevenzip.pull()

        assert check_output_mock.mock_calls == [
            call(
                ["7z", "x", os.path.join(new_dir, part_src_dir, fake_7z_file)],
                text=True,
                cwd="part-src-dir",
            )
        ]
        assert raised.value.exit_code == 1
