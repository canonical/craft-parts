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

import shutil
from pathlib import Path

import pytest
import yaml
from craft_parts import errors
from craft_parts.actions import Action, ActionType
from craft_parts.executor.part_handler import PartHandler
from craft_parts.filesystem_mounts import FilesystemMounts
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part
from craft_parts.state_manager.states import MigrationState
from craft_parts.steps import Step

from tests.unit.features.overlay import test_executor_part_handler

# pylint: disable=too-many-lines


@pytest.mark.usefixtures("new_dir")
class TestPartHandling(test_executor_part_handler.TestPartHandling):
    """Verify the part handler step processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {
                "plugin": "nil",
                "source": ".",
                "stage-packages": ["pkg1"],
                "stage-snaps": ["snap1"],
                "build-packages": ["pkg3"],
                "overlay-packages": ["pkg4"],
            },
            partitions=partitions,
        )
        self._project_info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=self._project_info,
            part_list=[self._part],
            base_layer_dir=Path("/base"),
        )
        self._part_info = PartInfo(self._project_info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        self._mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self._mock_mount_overlayfs = mocker.patch(
            "craft_parts.utils.os_utils.mount_overlayfs"
        )
        self._mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")
        # pylint: enable=attribute-defined-outside-init

    def test_run_overlay_script_move_to_partition(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mocker.patch("craft_parts.overlays.OverlayManager.install_packages")

        p1 = Part(
            "p1",
            {
                "plugin": "nil",
                "overlay-script": 'mv "$CRAFT_OVERLAY/foo1" "$CRAFT_MYPART_OVERLAY/"',
            },
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1], base_layer_dir=Path("/base")
        )
        part_info = PartInfo(info, p1)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        p1.part_layer_dir.mkdir(parents=True)
        file1 = p1.overlay_dir / "overlay" / "foo1"
        file2 = p1.overlay_dir / "overlay" / "bar1"
        file1.parent.mkdir(parents=True)

        file1.touch()
        file2.touch()

        handler._run_overlay(
            StepInfo(part_info, Step.OVERLAY), stdout=None, stderr=None
        )

        assert file1.exists() is False
        assert file2.is_file()
        assert (p1.part_layer_dirs["mypart"] / "foo1").is_file()
        assert (p1.part_layer_dirs["mypart"] / "bar1").exists() is False

    def test_run_overlay_with_filter(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mocker.patch("craft_parts.overlays.OverlayManager.install_packages")

        p1 = Part("p1", {"plugin": "nil", "overlay": ["-foo"]}, partitions=partitions)
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1], base_layer_dir=Path("/base")
        )
        part_info = PartInfo(info, p1)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        p1.part_layer_dir.mkdir(parents=True)
        file1 = p1.part_layer_dir / "foo"
        file2 = p1.part_layer_dir / "bar"

        file1.touch()
        file2.touch()

        handler._run_overlay(StepInfo(part_info, Step.PULL), stdout=None, stderr=None)

        assert file1.exists() is False
        assert file2.is_file()

    def test_run_build_without_overlay_visibility(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")

        p1 = Part("p1", {"plugin": "nil"}, partitions=partitions)
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1], base_layer_dir=Path("/base")
        )
        part_info = PartInfo(info, p1)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        handler._run_build(StepInfo(part_info, Step.BUILD), stdout=None, stderr=None)

        assert self._mock_mount_overlayfs.mock_calls == []

    # pylint: disable=too-many-arguments
    @pytest.mark.parametrize(
        ("step", "scriptlet"),
        [
            (Step.PULL, "override-pull"),
            (Step.OVERLAY, "overlay-script"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet(
        self, new_dir, partitions, mocker, capfd, step, scriptlet
    ):
        """If defined, scriptlets are executed instead of the built-in handler."""
        run_builtin_mock = mocker.patch(
            "craft_parts.executor.step_handler.StepHandler.run_builtin"
        )
        p1 = Part(
            "p1", {"plugin": "nil", scriptlet: "echo hello"}, partitions=partitions
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler._run_step(
            step_info=step_info,
            scriptlet_name=scriptlet,
            work_dir=Path(),
            stdout=None,
            stderr=None,
        )
        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == "+ echo hello\n"
        assert run_builtin_mock.mock_calls == []

    @pytest.mark.parametrize(
        ("step", "scriptlet"),
        [
            (Step.PULL, "override-pull"),
            (Step.OVERLAY, "overlay-script"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet_streams(
        self, new_dir, partitions, capfd, step, scriptlet
    ):
        p1 = Part(
            "p1",
            {"plugin": "nil", scriptlet: "echo hello; echo goodbye >&2"},
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=step)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        output_path = Path("output.txt")
        error_path = Path("error.txt")

        with output_path.open("w") as output, error_path.open("w") as error:
            handler._run_step(
                step_info=step_info,
                scriptlet_name=scriptlet,
                work_dir=Path(),
                stdout=output,
                stderr=error,
            )

        out, err = capfd.readouterr()
        assert out == ""
        assert err == ""
        assert output_path.read_text() == "hello\n"
        assert error_path.read_text() == "+ echo hello\n+ echo goodbye\ngoodbye\n"

    def test_compute_layer_hash(self, new_dir, partitions):
        p1 = Part(
            "p1", {"plugin": "nil", "overlay-packages": ["pkg1"]}, partitions=partitions
        )
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1, p2], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1, p2], overlay_manager=ovmgr
        )

        layer_hash = handler._compute_layer_hash(all_parts=False)
        assert layer_hash.hex() == "80ab51c6c76eb2b6fc01adc3143ebaf2b982ae56"

    def test_compute_layer_hash_for_all_parts(self, new_dir, partitions):
        p1 = Part(
            "p1", {"plugin": "nil", "overlay-packages": ["pkg1"]}, partitions=partitions
        )
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1, p2], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1, p2], overlay_manager=ovmgr
        )

        layer_hash = handler._compute_layer_hash(all_parts=True)
        assert layer_hash.hex() == "f4ae5a2ed1b4fd8a7e03f9264ab0f98ed6fd991b"


@pytest.mark.usefixtures("new_dir")
class TestPartUpdateHandler(test_executor_part_handler.TestPartUpdateHandler):
    """Verify step update processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {
                "plugin": "dump",
                "source": "subdir",
            },
            partitions=partitions,
        )
        Path("subdir").mkdir()
        Path("subdir/foo.txt").write_text("content")

        self._project_info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=self._project_info,
            part_list=[self._part],
            base_layer_dir=Path("/base"),
        )
        self._part_info = PartInfo(self._project_info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        # pylint: enable=attribute-defined-outside-init


@pytest.mark.usefixtures("new_dir")
class TestPartReapplyHandler(test_executor_part_handler.TestPartReapplyHandler):
    """Verify step reapplication processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {"plugin": "nil", "overlay-script": "touch bar.txt"},
            partitions=partitions,
        )
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=new_dir
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )

        mocker.patch("craft_parts.utils.os_utils.mount")
        mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
        mocker.patch("craft_parts.utils.os_utils.umount")
        # pylint: enable=attribute-defined-outside-init

    def test_reapply_overlay(self):
        self._handler.run_action(Action("foo.txt", Step.PULL))

        Path("parts/foo/layer/foo.txt").touch()
        Path("partitions/mypart/parts/foo/layer/foo.txt").touch()

        self._handler.run_action(Action("foo", Step.OVERLAY, ActionType.REAPPLY))

        assert Path("parts/foo/layer/foo.txt").exists() is False
        assert Path("parts/foo/layer/bar.txt").exists()
        assert Path("partitions/mypart/parts/foo/layer/foo.txt").exists() is False

    @pytest.mark.parametrize("step", [Step.PULL, Step.BUILD, Step.STAGE, Step.PRIME])
    def test_reapply_invalid(self, step):
        with pytest.raises(errors.InvalidAction):
            self._handler.run_action(Action("foo", step, ActionType.REAPPLY))


@pytest.mark.usefixtures("new_dir")
class TestOverlayMigration:
    """Overlay migration to stage and prime test cases"""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        p1 = Part(
            "p1",
            {
                "plugin": "nil",
                "overlay-script": 'mv "$CRAFT_OVERLAY/bar" "$CRAFT_MYPART_OVERLAY"',
            },
            partitions=partitions,
        )
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        p3 = Part("p3", {"plugin": "nil"}, partitions=partitions)

        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1, p2, p3], base_layer_dir=None
        )

        self._p1_handler = PartHandler(
            p1,
            part_info=PartInfo(info, p1),
            part_list=[p1, p2, p3],
            overlay_manager=ovmgr,
        )
        self._p2_handler = PartHandler(
            p2,
            part_info=PartInfo(info, p2),
            part_list=[p1, p2, p3],
            overlay_manager=ovmgr,
        )
        self._p3_handler = PartHandler(
            p3,
            part_info=PartInfo(info, p3),
            part_list=[p1, p2, p3],
            overlay_manager=ovmgr,
        )

        self._p1_handler._make_dirs()
        self._p2_handler._make_dirs()
        self._p3_handler._make_dirs()

        # populate layers
        Path(p1.part_layer_dir, "dir1").mkdir()
        Path(p1.part_layer_dir, "dir1/foo").touch()
        Path(p1.part_layer_dirs["mypart"], "bar").touch()

        Path(p2.part_layer_dir, "dir1").mkdir()
        Path(p2.part_layer_dir, "dir1/baz").touch()
        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_migrate_overlay_with_partitions(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_migrated_overlay_with_partitions(
        self, mocker, new_dir, step, step_dir
    ):
        wh = Path("parts/p2/layer/dir1/foo")
        wh.touch()
        mocker.patch(
            "craft_parts.overlays.is_whiteout_file", new=lambda x: x == new_dir / wh
        )

        opaque = Path("parts/p2/layer/dir2")
        opaque.mkdir()
        mocker.patch(
            "craft_parts.overlays.is_opaque_dir", new=lambda x: x == new_dir / opaque
        )

        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists() is False
        assert Path(f"{step_dir}/dir1/.wh.foo").exists()
        assert Path(f"{step_dir}/dir2/.wh..wh..opq").exists()
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/.wh.foo").exists() is False
        assert Path(f"{step_dir}/dir2").exists() is False
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/dir1/baz").exists() is False
        assert Path(f"overlay/{step_dir}_overlay").exists() is False

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_stage_overlay_multiple_parts_with_partitions(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        _run_step_migration(self._p2_handler, step)

        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        self._p2_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/foo").exists() is False
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/dir1/baz").exists() is False
        assert Path(f"overlay/{step_dir}_overlay").exists() is False

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_overlay_shared_file_with_partitions(self, mocker, step, step_dir):
        Path("parts/p1/layer/file1").write_text("content")
        Path("parts/p3/install/file1").write_text("content")

        _run_step_migration(self._p2_handler, step)
        _run_step_migration(self._p3_handler, step)
        assert Path(f"{step_dir}/file1").exists()
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()

        # clean overlay data
        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/file1").exists()  # file1 remains (also belongs to p3)

        # clean part data
        self._p3_handler.clean_step(step)
        assert Path(f"{step_dir}/file1").exists() is False


@pytest.mark.usefixtures("new_dir")
class TestOverlayMigrationFilesystems:
    """Overlay migration to stage and prime test cases with a non-default filesystems."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        filesystem_mounts = FilesystemMounts.unmarshal(
            {
                "default": [
                    {
                        "mount": "/",
                        "device": "default",
                    },
                    {
                        "mount": "/foo",
                        "device": "mypart",
                    },
                ]
            }
        )
        p1 = Part(
            "p1", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )

        info = ProjectInfo(
            application_name="test",
            cache_dir=new_dir,
            partitions=partitions,
            filesystem_mounts=filesystem_mounts,
        )
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1, p2], base_layer_dir=None
        )

        self._p1_handler = PartHandler(
            p1,
            part_info=PartInfo(info, p1),
            part_list=[p1, p2],
            overlay_manager=ovmgr,
        )
        self._p2_handler = PartHandler(
            p2,
            part_info=PartInfo(info, p2),
            part_list=[p1, p2],
            overlay_manager=ovmgr,
        )

        self._p1_handler._make_dirs()
        self._p2_handler._make_dirs()

        # populate layers
        Path(p1.part_layer_dir, "dir1").mkdir()
        Path(p1.part_layer_dir, "dir1/a").touch()
        Path(p1.part_layer_dir, "foo").mkdir()
        Path(p1.part_layer_dir, "foo/bar").touch()

        Path(p2.part_layer_dir, "dir1").mkdir()
        Path(p2.part_layer_dir, "dir1/baz").touch()
        Path(p2.part_layer_dir, "foo").mkdir()
        Path(p2.part_layer_dir, "foo/qux").touch()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_write_overlay_migration_states(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        _run_step_migration(self._p2_handler, step)

        default_overlay_state_path = Path(f"overlay/{step_dir}_overlay")
        mypart_overlay_state_path = Path(
            f"partitions/mypart/overlay/{step_dir}_overlay"
        )
        yourpart_overlay_state_path = Path(
            f"partitions/yourpart/overlay/{step_dir}_overlay"
        )

        assert default_overlay_state_path.exists()
        assert mypart_overlay_state_path.exists()
        assert yourpart_overlay_state_path.exists()

        default_overlay_state = _load_migration_state(default_overlay_state_path)
        mypart_overlay_state = _load_migration_state(mypart_overlay_state_path)
        yourpart_overlay_state = _load_migration_state(yourpart_overlay_state_path)

        assert default_overlay_state.files == {"dir1/a", "dir1/baz"}
        assert default_overlay_state.directories == {"dir1", "foo"}
        assert mypart_overlay_state.files == {"bar", "qux"}
        assert mypart_overlay_state.directories == set()
        assert yourpart_overlay_state.files == set()
        assert yourpart_overlay_state.directories == set()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_write_overlay_migration_empty_states(self, step, step_dir):
        # Empty the layers, so nothing will be staged nor primed
        # from the overlay
        shutil.rmtree(self._p1_handler._part.part_layer_dir)
        self._p1_handler._part.part_layer_dir.mkdir()
        shutil.rmtree(self._p2_handler._part.part_layer_dir)
        self._p2_handler._part.part_layer_dir.mkdir()

        _run_step_migration(self._p1_handler, step)
        _run_step_migration(self._p2_handler, step)

        default_overlay_state_path = Path(f"overlay/{step_dir}_overlay")
        mypart_overlay_state_path = Path(
            f"partitions/mypart/overlay/{step_dir}_overlay"
        )
        yourpart_overlay_state_path = Path(
            f"partitions/yourpart/overlay/{step_dir}_overlay"
        )

        assert default_overlay_state_path.exists()
        assert mypart_overlay_state_path.exists()
        assert yourpart_overlay_state_path.exists()

        default_overlay_state = _load_migration_state(default_overlay_state_path)
        mypart_overlay_state = _load_migration_state(mypart_overlay_state_path)
        yourpart_overlay_state = _load_migration_state(yourpart_overlay_state_path)

        assert default_overlay_state.files == set()
        assert default_overlay_state.directories == set()
        assert mypart_overlay_state.files == set()
        assert mypart_overlay_state.directories == set()
        assert yourpart_overlay_state.files == set()
        assert yourpart_overlay_state.directories == set()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_stage_overlay_multiple_parts_with_partitions(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        _run_step_migration(self._p2_handler, step)

        assert Path(f"{step_dir}/dir1/a").exists()
        # File bar was successfully distributed to mypart
        assert Path(f"partitions/mypart/{step_dir}/bar").exists()
        assert Path(f"{step_dir}/foo").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"partitions/mypart/{step_dir}/qux").exists()

        self._p1_handler.clean_step(step)
        self._p2_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/a").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/foo").exists() is False
        assert Path(f"{step_dir}/dir1/baz").exists() is False
        assert Path(f"partitions/mypart/{step_dir}/qux").exists() is False


def _load_migration_state(state_path: Path) -> MigrationState:
    with open(state_path) as yaml_file:
        state_data = yaml.safe_load(yaml_file)

    return MigrationState.unmarshal(state_data)


def _run_step_migration(handler: PartHandler, step: Step) -> None:
    if step > Step.STAGE:
        handler.run_action(Action("", Step.STAGE))
    handler.run_action(Action("", step))


@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler(test_executor_part_handler.TestPartCleanHandler):
    """Verify step update processing."""


@pytest.mark.usefixtures("new_dir")
class TestRerunStep(test_executor_part_handler.TestRerunStep):
    """Verify rerun actions."""


@pytest.mark.usefixtures("new_dir")
class TestFileFilter(test_executor_part_handler.TestFileFilter):
    """File filter test cases."""


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_executor_part_handler.TestHelpers):
    """Verify helper functions."""
