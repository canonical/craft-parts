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

from pathlib import Path

import pytest
from craft_parts import errors
from craft_parts.actions import Action, ActionType
from craft_parts.executor import part_handler
from craft_parts.executor.part_handler import PartHandler
from craft_parts.executor.step_handler import StagePartitionContents, StepContents
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step

from tests.unit.executor import test_part_handler

# pylint: disable=too-many-lines


@pytest.mark.usefixtures("new_dir")
class TestPartHandling(test_part_handler.TestPartHandling):
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
        self._project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
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

    def test_run_overlay(self, mocker):
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mocker.patch("craft_parts.overlays.OverlayManager.install_packages")

        state = self._handler._run_overlay(
            StepInfo(self._part_info, Step.OVERLAY), stdout=None, stderr=None
        )
        assert state == states.OverlayState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
        )

    def test_run_overlay_with_filter(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mocker.patch("craft_parts.overlays.OverlayManager.install_packages")

        p1 = Part("p1", {"plugin": "nil", "overlay": ["-foo"]}, partitions=partitions)
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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

    def test_run_build(self, mocker):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")
        mocker.patch(
            "craft_parts.packages.Repository.get_installed_packages",
            return_value=["hello=2.10"],
        )
        mocker.patch(
            "craft_parts.packages.snaps.get_installed_snaps",
            return_value=["snapcraft=6466"],
        )
        mocker.patch("subprocess.check_output", return_value=b"os-info")

        state = self._handler._run_build(
            StepInfo(self._part_info, Step.BUILD), stdout=None, stderr=None
        )
        assert state == states.BuildState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            assets={
                "build-packages": ["pkg3"],
                "build-snaps": [],
                "uname": "os-info",
                "installed-packages": ["hello=2.10"],
                "installed-snaps": ["snapcraft=6466"],
            },
            overlay_hash="d12e3f53ba91f94656abc940abb50b12b209d246",
        )

        self._mock_mount_overlayfs.assert_called_with(
            f"{self._part_info.overlay_mount_dir}",
            (
                f"-olowerdir={self._part_info.overlay_packages_dir}:/base,"
                f"upperdir={self._part.part_layer_dir},"
                f"workdir={self._part_info.overlay_work_dir}"
            ),
        )
        self._mock_umount.assert_called_with(f"{self._part_info.overlay_mount_dir}")

    def test_run_build_without_overlay_visibility(self, mocker, new_dir, partitions):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")

        p1 = Part("p1", {"plugin": "nil"}, partitions=partitions)
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1], base_layer_dir=Path("/base")
        )
        part_info = PartInfo(info, p1)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        handler._run_build(StepInfo(part_info, Step.BUILD), stdout=None, stderr=None)

        assert self._mock_mount_overlayfs.mock_calls == []

    def test_run_stage(self, mocker):
        mock_step_contents = StepContents(stage=True)
        mock_step_contents.partitions_contents["default"] = StagePartitionContents(
            files={"file"},
            dirs={"dir"},
            backstage_files={"back_file"},
            backstage_dirs={"back_dir"},
        )
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_stage",
            return_value=mock_step_contents,
        )

        state = self._handler._run_stage(
            StepInfo(self._part_info, Step.STAGE), stdout=None, stderr=None
        )
        assert state == states.StageState(
            partition="default",
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
            backstage_files={"back_file"},
            backstage_directories={"back_dir"},
            overlay_hash="d12e3f53ba91f94656abc940abb50b12b209d246",
        )

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
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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

    # pylint: enable=too-many-arguments

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
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
class TestPartUpdateHandler(test_part_handler.TestPartUpdateHandler):
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

        self._project_info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
class TestPartReapplyHandler:
    """Verify step reapplication processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {"plugin": "nil", "overlay-script": "touch bar.txt"},
            partitions=partitions,
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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

        self._handler.run_action(Action("foo", Step.OVERLAY, ActionType.REAPPLY))

        assert Path("parts/foo/layer/foo.txt").exists() is False
        assert Path("parts/foo/layer/bar.txt").exists()

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
            "p1", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        p3 = Part("p3", {"plugin": "nil"}, partitions=partitions)

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
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
        Path(p1.part_layer_dir, "bar").touch()

        Path(p2.part_layer_dir, "dir1").mkdir()
        Path(p2.part_layer_dir, "dir1/baz").touch()
        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_migrate_overlay(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_migrate_overlay_whiteout_translation(
        self, mocker, new_dir, step, step_dir
    ):
        wh = Path("parts/p2/layer/dir1/foo")
        wh.touch()
        mocker.patch(
            "craft_parts.overlays.is_whiteout_file", new=lambda x: x == new_dir / wh
        )

        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists() is False
        assert Path(f"{step_dir}/dir1/.wh.foo").exists()
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_migrate_overlay_opaque_dir_translation(
        self, mocker, new_dir, step, step_dir
    ):
        opaque = Path("parts/p2/layer/dir1")
        mocker.patch(
            "craft_parts.overlays.is_opaque_dir", new=lambda x: x == new_dir / opaque
        )

        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/.wh..wh..opq").exists()
        assert Path(f"{step_dir}/dir1/foo").exists() is False
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_migrated_overlay(self, mocker, new_dir, step, step_dir):
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
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/.wh.foo").exists() is False
        assert Path(f"{step_dir}/dir2").exists() is False
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/dir1/baz").exists() is False
        assert Path(f"overlay/{step_dir}_overlay").exists() is False

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_stage_overlay_multiple_parts(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        _run_step_migration(self._p2_handler, step)

        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

        self._p2_handler.clean_step(step)
        assert Path(f"{step_dir}/dir1/foo").exists() is False
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/dir1/baz").exists() is False
        assert Path(f"overlay/{step_dir}_overlay").exists() is False

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_overlay_shared_file(self, mocker, step, step_dir):
        Path("parts/p1/layer/file1").write_text("content")
        Path("parts/p3/install/file1").write_text("content")

        _run_step_migration(self._p2_handler, step)
        _run_step_migration(self._p3_handler, step)
        assert Path(f"{step_dir}/file1").exists()
        assert Path(f"{step_dir}/bar").exists()

        # clean overlay data
        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/bar").exists() is False
        assert Path(f"{step_dir}/file1").exists()  # file1 remains (also belongs to p3)

        # clean part data
        self._p3_handler.clean_step(step)
        assert Path(f"{step_dir}/file1").exists() is False

    @pytest.mark.parametrize(
        ("step", "step_dir"), [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_part_shared_file(self, mocker, step, step_dir):
        Path("parts/p1/layer/file1").write_text("content")
        Path("parts/p3/install/file1").write_text("content")

        _run_step_migration(self._p2_handler, step)
        _run_step_migration(self._p3_handler, step)
        assert Path(f"{step_dir}/file1").exists()
        assert Path(f"{step_dir}/bar").exists()

        # clean part data
        self._p3_handler.clean_step(step)
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/file1").exists()  # file1 remains (also belongs to p1)

        # clean overlay data
        self._p1_handler.clean_step(step)
        assert Path(f"{step_dir}/file1").exists() is False

    def test_migrate_overlay_filter_whiteout(self, mocker, new_dir, partitions):
        cache_dir = new_dir / "cache"
        base_dir = new_dir / "base"
        cache_dir.mkdir()
        base_dir.mkdir()

        p1 = Part(
            "p1", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        info = ProjectInfo(application_name="test", cache_dir=cache_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[p1], base_layer_dir=base_dir
        )
        p1_handler = PartHandler(
            p1,
            part_info=PartInfo(info, p1),
            part_list=[p1],
            overlay_manager=ovmgr,
        )
        p1_handler._make_dirs()

        wh1 = p1.part_layer_dir / "file1"
        wh2 = p1.part_layer_dir / "file2"
        wh1.touch()
        wh2.touch()
        mocker.patch(
            "craft_parts.overlays.is_whiteout_file", new=lambda x: x in (wh1, wh2)
        )

        Path(base_dir, "file2").touch()  # file2 has a backing file

        _run_step_migration(p1_handler, Step.PRIME)
        assert Path("prime/.wh.file1").exists() is False
        assert Path("prime/.wh.file2").exists()


def _run_step_migration(handler: PartHandler, step: Step) -> None:
    if step > Step.STAGE:
        handler.run_action(Action("", Step.STAGE))
    handler.run_action(Action("", step))


@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler(test_part_handler.TestPartCleanHandler):
    """Verify step update processing."""


@pytest.mark.usefixtures("new_dir")
class TestRerunStep(test_part_handler.TestRerunStep):
    """Verify rerun actions."""


@pytest.mark.usefixtures("new_dir")
class TestPackages(test_part_handler.TestPackages):
    """Verify package handling."""


@pytest.mark.usefixtures("new_dir")
class TestFileFilter(test_part_handler.TestFileFilter):
    """File filter test cases."""


@pytest.mark.usefixtures("new_dir")
class TestHelpers(test_part_handler.TestHelpers):
    """Verify helper functions."""

    @pytest.mark.parametrize("step", list(Step))
    def test_parts_with_overlay_in_step(self, partitions, step):
        p1 = Part("p1", {"plugin": "nil"}, partitions=partitions)
        p2 = Part(
            "p2", {"plugin": "nil", "overlay-script": "ls"}, partitions=partitions
        )
        p3 = Part(
            "p3", {"plugin": "nil", "overlay-packages": ["pkg1"]}, partitions=partitions
        )
        p4 = Part("p4", {"plugin": "nil", "overlay": ["/etc"]}, partitions=partitions)

        res = part_handler._parts_with_overlay_in_step(step, part_list=[p1, p2, p3, p4])
        assert res == []

        for part in [p1, p2, p3, p4]:
            state_path = states.get_step_state_path(part, step)
            state_path.parent.mkdir(parents=True)
            state_path.touch()

        res = part_handler._parts_with_overlay_in_step(step, part_list=[p1, p2, p3, p4])
        assert res == [p2, p3, p4]
