# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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
from collections.abc import Iterator

import pytest
from craft_parts import Action, Step
from craft_parts.executor import filesets, part_handler
from craft_parts.executor.errors import EnvironmentChangedError
from craft_parts.executor.part_handler import PartHandler
from craft_parts.infos import PartInfo, ProjectInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part

from tests.unit.executor import test_part_handler

PARTITIONS = ["default", "mypart", "yourpart", "our/special-part"]
TEST_FILES = ["filea", "dir1/file1a", "dir1/file1b", "dir2/dir3/file2a"]
ALL_FILES = {f"{partition}/{file}" for file in TEST_FILES for partition in PARTITIONS}


@pytest.mark.usefixtures("new_dir")
class TestPartHandling(test_part_handler.TestPartHandling):
    """Part handling tests with partitions enabled"""


@pytest.mark.usefixtures("new_dir")
class TestPartUpdateHandler(test_part_handler.TestPartUpdateHandler):
    """Verify step update processing with partitions enabled."""

    _update_build_path = pathlib.Path("parts/foo/install/foo.txt")


@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler(test_part_handler.TestPartCleanHandler):
    """Verify step update processing."""

    @pytest.mark.parametrize(
        ("step", "test_dir", "state_file"),
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install", "build"),
            (Step.STAGE, "stage", "stage"),
            (Step.PRIME, "prime", "prime"),
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


@pytest.mark.usefixtures("new_dir")
class TestRerunStep(test_part_handler.TestRerunStep):
    """Verify rerun actions."""


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package handling."""


class TestFileFilter(test_part_handler.TestFileFilter):
    """File filter test cases."""

    _destdir = pathlib.Path("destdir")

    def _iter_files(self, partitions: set[str]) -> Iterator[str]:
        """Iterate over the partitions and files to test."""
        for partition, file in itertools.product(partitions, TEST_FILES):
            yield f"{partition}/{file}"

    @pytest.fixture
    def make_files(self, new_dir, partitions):
        for file in self._iter_files(partitions):
            path = self._destdir / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    @pytest.mark.parametrize(
        ("filters", "survivors"),
        [
            ([], ALL_FILES),
            (["*"], ALL_FILES),
            (["(default)/"], ALL_FILES),
            (["(default)/*"], ALL_FILES),
            (["-filea"], ALL_FILES - {"default/filea"}),
            (
                ["filea", "(mypart)/dir1", "(yourpart)/*"],
                {
                    "default/filea",
                    "mypart/dir1/file1a",
                    "mypart/dir1/file1b",
                    "yourpart/filea",
                    "yourpart/dir1/file1a",
                    "yourpart/dir1/file1b",
                    "yourpart/dir2/dir3/file2a",
                    "our/special-part/filea",
                    "our/special-part/dir1/file1a",
                    "our/special-part/dir1/file1b",
                    "our/special-part/dir2/dir3/file2a",
                },
            ),
            (
                [
                    "-(default)/*",
                    "-(mypart)/*",
                    "(yourpart)/filea",
                    "-(our/special-part)/*",
                ],
                {"yourpart/filea"},
            ),
        ],
    )
    def test_apply_partition_aware_filter(
        self, make_files, new_dir, survivors, filters, partitions
    ):
        fileset = filesets.Fileset(filters)

        for partition in partitions:
            files, dirs = filesets.migratable_filesets(
                fileset, str(self._destdir / partition), "default", partition
            )
            part_handler._apply_file_filter(
                filter_files=files, filter_dirs=dirs, destdir=self._destdir / partition
            )

        for file in self._iter_files(partitions):
            assert (self._destdir / file).exists() == (file in survivors)


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_part_handler.TestHelpers):
    """Test helpers with partitions enabled."""


@pytest.mark.usefixtures("new_dir")
class TestDirs(test_part_handler.TestDirs):
    """Test project dirs handling."""

    def test_makedirs_swap_partitions(self, new_dir):
        partitions = ["mypart", "yourpart", "our/special-part"]

        def setup_handler(partitions) -> PartHandler:
            part = Part(
                "foo",
                {
                    "plugin": "nil",
                    "source": ".",
                },
                partitions=partitions,
            )
            info = ProjectInfo(
                application_name="test", cache_dir=new_dir, partitions=partitions
            )
            part_info = PartInfo(info, part)
            ovmgr = OverlayManager(
                project_info=info,
                part_list=[part],
                base_layer_dir=None,
                cache_level=0,
            )
            return PartHandler(
                part,
                part_info=part_info,
                part_list=[part],
                overlay_manager=ovmgr,
            )

        handler = setup_handler(partitions)
        handler._make_dirs()

        # swap first 2 partitions
        partitions = ["yourpart", "mypart", "our/special-part"]
        handler = setup_handler(partitions)

        with pytest.raises(EnvironmentChangedError):
            handler._make_dirs()

    def test_makedirs_usrmerged_partitions(self, new_dir):
        """Test the behavior when 'usrmerged_by_default' is True and we have partitions."""
        partitions = ["one", "two", "three"]
        part, handler = self._part_and_handler(
            usrmerged_by_default=True, new_dir=new_dir, partitions=partitions
        )
        handler._make_dirs()

        # The default partition gets usrmerged; the others don't.
        self._assert_usrmerged(part.part_install_dirs["one"])
        assert list(part.part_install_dirs["two"].iterdir()) == []
        assert list(part.part_install_dirs["three"].iterdir()) == []
