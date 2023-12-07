# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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
import itertools
import pathlib
from typing import Iterator

import pytest
from craft_parts import Action, Step
from craft_parts.executor import filesets, part_handler

from tests.unit.executor import test_part_handler

PARTITIONS = ["default", "mypart", "yourpart"]
TEST_FILES = ["filea", "dir1/file1a", "dir1/file1b", "dir2/dir3/file2a"]


@pytest.mark.xfail(
    reason="fails to create envvars for namespaced partitions, will be fixed by #597"
)
@pytest.mark.usefixtures("new_dir")
class TestPartHandling(test_part_handler.TestPartHandling):
    """Part handling tests with partitions enabled"""


@pytest.mark.xfail(
    reason="fails to create envvars for namespaced partitions, will be fixed by #597"
)
@pytest.mark.usefixtures("new_dir")
class TestPartUpdateHandler(test_part_handler.TestPartUpdateHandler):
    """Verify step update processing with partitions enabled."""

    _update_build_path = pathlib.Path("parts/foo/install/default/foo.txt")


@pytest.mark.xfail(
    reason="fails to create envvars for namespaced partitions, will be fixed by #597"
)
@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler(test_part_handler.TestPartCleanHandler):
    """Verify step update processing."""

    @pytest.mark.parametrize(
        ("step", "test_dir", "state_file"),
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install/default", "build"),
            (Step.STAGE, "stage/default", "stage"),
            (Step.PRIME, "prime/default", "prime"),
        ],
    )
    def test_clean_step(self, mocker, step, test_dir, state_file):
        self._handler._make_dirs()
        for each_step in [*step.previous_steps(), step]:
            self._handler.run_action(Action("foo", each_step))

        assert pathlib.Path(test_dir, "foo.txt").is_file()
        assert pathlib.Path(test_dir, "bar").is_dir()
        assert pathlib.Path(f"parts/foo/state/{state_file}").is_file()

        self._handler.clean_step(step)

        assert not pathlib.Path(test_dir, "foo.txt").is_file()
        assert not pathlib.Path(test_dir, "bar").is_dir()
        assert not pathlib.Path(f"parts/foo/state/{state_file}").is_file()


@pytest.mark.xfail(
    reason="fails to create envvars for namespaced partitions, will be fixed by #597"
)
@pytest.mark.usefixtures("new_dir")
class TestRerunStep(test_part_handler.TestRerunStep):
    """Verify rerun actions."""


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package handling."""


class TestFileFilter(test_part_handler.TestFileFilter):
    """File filter test cases."""

    _destdir = pathlib.Path("destdir")
    _default_destdir = pathlib.Path("destdir/default")

    def _iter_files(self) -> Iterator[str]:
        """Iterate over the partitions and files to test."""
        for partition, file in itertools.product(PARTITIONS, TEST_FILES):
            yield f"{partition}/{file}"

    @pytest.fixture()
    def make_files(
        self,
        new_dir,
    ):
        for file in self._iter_files():
            path = self._destdir / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    @pytest.mark.parametrize(
        ("filters", "survivors"),
        [
            (
                [],
                {
                    f"{partition}/{file}"
                    for partition, file in itertools.product(PARTITIONS, TEST_FILES)
                },
            ),
            (
                ["-filea"],
                {
                    "default/dir1/file1a",
                    "default/dir1/file1b",
                    "default/dir2/dir3/file2a",
                    "mypart/filea",
                    "mypart/dir1/file1a",
                    "mypart/dir1/file1b",
                    "mypart/dir2/dir3/file2a",
                    "yourpart/filea",
                    "yourpart/dir1/file1a",
                    "yourpart/dir1/file1b",
                    "yourpart/dir2/dir3/file2a",
                },
            ),
            (
                ["filea", "(mypart)/dir1", "(yourpart)"],
                {
                    "default/filea",
                    "mypart/dir1/file1a",
                    "mypart/dir1/file1b",
                    "yourpart/filea",
                    "yourpart/dir1/file1a",
                    "yourpart/dir1/file1b",
                    "yourpart/dir2/dir3/file2a",
                },
            ),
            (["-(default)", "-(mypart)", "(yourpart)/filea"], {"yourpart/filea"}),
        ],
    )
    def test_apply_partition_aware_filter(
        self, make_files, new_dir, survivors, filters
    ):
        fileset = filesets.Fileset(filters)

        files, dirs = filesets.migratable_filesets(fileset, str(self._destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=self._destdir
        )

        for file in self._iter_files():
            assert (self._destdir / file).exists() == (file in survivors)


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_part_handler.TestHelpers):
    """Test helpers with partitions enabled."""
