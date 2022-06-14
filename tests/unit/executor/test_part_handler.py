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

import logging
import os
from pathlib import Path
from typing import cast

import pytest

from craft_parts import errors, packages
from craft_parts.actions import Action, ActionType
from craft_parts.executor import filesets, part_handler
from craft_parts.executor.part_handler import PartHandler
from craft_parts.executor.step_handler import StepContents
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.overlays import OverlayManager
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step
from craft_parts.utils import os_utils

# pylint: disable=too-many-lines


@pytest.mark.usefixtures("new_dir")
class TestPartHandling:
    """Verify the part handler step processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
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
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=Path("/base")
        )
        self._part_info = PartInfo(info, self._part)
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

    def test_run_pull(self, mocker):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_pull")
        mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        mocker.patch("craft_parts.packages.snaps.download_snaps")
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")

        state = self._handler._run_pull(
            StepInfo(self._part_info, Step.PULL), stdout=None, stderr=None
        )
        assert state == states.PullState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            assets={
                "stage-packages": ["pkg1", "pkg2"],
                "stage-snaps": ["snap1"],
                "source-details": None,
            },
        )

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

    def test_run_overlay_with_filter(self, mocker, new_dir):
        mocker.patch("craft_parts.overlays.OverlayManager.download_packages")
        mocker.patch("craft_parts.overlays.OverlayManager.install_packages")

        p1 = Part("p1", {"plugin": "nil", "overlay": ["-foo"]})
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

    @pytest.mark.usefixtures("new_dir")
    @pytest.mark.parametrize("out_of_source", [True, False])
    def test_run_build_out_of_source_behavior(self, mocker, out_of_source):
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

        mocker.patch(
            "craft_parts.plugins.plugins.NilPlugin.out_of_source_build",
            return_value=out_of_source,
            new_callable=mocker.PropertyMock,
        )

        self._part_info.part_src_dir.mkdir(parents=True)
        source_file = self._part_info.part_src_dir / "source.c"
        source_file.write_text('printf("hello\n");', encoding="UTF-8")

        self._handler._run_build(
            StepInfo(self._part_info, Step.BUILD), stdout=None, stderr=None
        )

        # Check that 'source.c' exists in the source dir but not build dir.
        assert (self._part_info.part_src_dir / "source.c").exists()
        assert (
            self._part_info.part_build_dir / "source.c"
        ).exists() is not out_of_source

    def test_run_build_without_overlay_visibility(self, mocker, new_dir):
        mocker.patch("craft_parts.executor.step_handler.StepHandler._builtin_build")

        p1 = Part("p1", {"plugin": "nil"})
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
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_stage",
            return_value=StepContents({"file"}, {"dir"}),
        )

        state = self._handler._run_stage(
            StepInfo(self._part_info, Step.STAGE), stdout=None, stderr=None
        )
        assert state == states.StageState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
            overlay_hash="d12e3f53ba91f94656abc940abb50b12b209d246",
        )

    def test_run_prime(self, mocker):
        mocker.patch(
            "craft_parts.executor.step_handler.StepHandler._builtin_prime",
            return_value=StepContents({"file"}, {"dir"}),
        )

        state = self._handler._run_prime(
            StepInfo(self._part_info, Step.PRIME), stdout=None, stderr=None
        )
        assert state == states.PrimeState(
            part_properties=self._part.spec.marshal(),
            project_options=self._part_info.project_options,
            files={"file"},
            directories={"dir"},
        )

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.OVERLAY, "overlay-script"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet(self, new_dir, capfd, step, scriptlet):
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello"})
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

    @pytest.mark.parametrize(
        "step,scriptlet",
        [
            (Step.PULL, "override-pull"),
            (Step.OVERLAY, "overlay-script"),
            (Step.BUILD, "override-build"),
            (Step.STAGE, "override-stage"),
            (Step.PRIME, "override-prime"),
        ],
    )
    def test_run_step_scriptlet_streams(self, new_dir, capfd, step, scriptlet):
        p1 = Part("p1", {"plugin": "nil", scriptlet: "echo hello; echo goodbye >&2"})
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

    def test_compute_layer_hash(self, new_dir):
        p1 = Part("p1", {"plugin": "nil", "overlay-packages": ["pkg1"]})
        p2 = Part("p2", {"plugin": "nil", "overlay-script": "ls"})
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

    def test_compute_layer_hash_for_all_parts(self, new_dir):
        p1 = Part("p1", {"plugin": "nil", "overlay-packages": ["pkg1"]})
        p2 = Part("p2", {"plugin": "nil", "overlay-script": "ls"})
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
class TestPartUpdateHandler:
    """Verify step update processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part(
            "foo",
            {
                "plugin": "dump",
                "source": "subdir",
            },
        )
        Path("subdir").mkdir()
        Path("subdir/foo.txt").write_text("content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        # pylint: enable=attribute-defined-outside-init

    def test_update_pull(self):
        self._handler.run_action(Action("foo", Step.PULL))

        source_file = Path("subdir/foo.txt")
        os_utils.TimedWriter.write_text(source_file, "change")
        Path("parts/foo/src/bar.txt").touch()

        self._handler.run_action(Action("foo", Step.PULL, ActionType.UPDATE))

        assert Path("parts/foo/src/foo.txt").read_text() == "change"
        assert Path("parts/foo/src/bar.txt").exists()

    def test_update_pull_no_source(self, new_dir, caplog):
        caplog.set_level(logging.WARNING)
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, part=p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        assert handler._source_handler is None

        # this shouldn't fail
        handler.run_action(Action("p1", Step.PULL, ActionType.UPDATE))

        assert caplog.records[0].message == (
            "Update requested on part 'p1' without a source handler."
        )

    def test_update_pull_with_scriptlet(self, new_dir, capfd):
        p1 = Part("p1", {"plugin": "nil", "override-pull": "echo hello"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        handler.run_action(Action("foo", Step.PULL, ActionType.UPDATE))

        out, err = capfd.readouterr()
        assert out == "hello\n"
        assert err == "+ echo hello\n"

    def test_update_build(self):
        self._handler._make_dirs()
        self._handler.run_action(Action("foo", Step.PULL))
        self._handler.run_action(Action("foo", Step.OVERLAY))
        self._handler.run_action(Action("foo", Step.BUILD))

        source_file = Path("subdir/foo.txt")
        os_utils.TimedWriter.write_text(source_file, "change")

        self._handler.run_action(Action("foo", Step.BUILD, ActionType.UPDATE))

        assert Path("parts/foo/install/foo.txt").read_text() == "change"

    def test_update_build_stage_packages(self, new_dir, mocker):
        def fake_unpack(**_):
            Path("parts/foo/install/hello").touch()

        mocker.patch(
            "craft_parts.packages.Repository.unpack_stage_packages", new=fake_unpack
        )
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )

        part = Part(
            "foo",
            {"plugin": "dump", "source": "subdir", "stage-packages": ["pkg"]},
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(project_info=info, part_list=[part], base_layer_dir=None)
        part_info = PartInfo(info, part)
        handler = PartHandler(
            part,
            part_info=part_info,
            part_list=[part],
            overlay_manager=ovmgr,
        )
        handler._make_dirs()
        handler.run_action(Action("foo", Step.PULL))
        handler.run_action(Action("foo", Step.OVERLAY))
        handler.run_action(Action("foo", Step.BUILD))

        assert Path("parts/foo/install/hello").exists()

        handler.run_action(Action("foo", Step.BUILD, ActionType.UPDATE))

        assert Path("parts/foo/install/hello").exists()

    @pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
    def test_update_invalid(self, step):
        with pytest.raises(errors.InvalidAction):
            self._handler.run_action(Action("foo", step, ActionType.UPDATE))


@pytest.mark.usefixtures("new_dir")
class TestPartReapplyHandler:
    """Verify step reapplication processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part("foo", {"plugin": "nil", "overlay-script": "touch bar.txt"})
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

        Path("parts/foo/layer/foo").touch()

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
    def setup_method_fixture(self, new_dir):
        # pylint: disable=attribute-defined-outside-init
        p1 = Part("p1", {"plugin": "nil", "overlay-script": "ls"})
        p2 = Part("p2", {"plugin": "nil", "overlay-script": "ls"})
        p3 = Part("p3", {"plugin": "nil"})

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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_migrate_overlay(self, step, step_dir):
        _run_step_migration(self._p1_handler, step)
        assert Path(f"{step_dir}/dir1/foo").exists()
        assert Path(f"{step_dir}/bar").exists()
        assert Path(f"{step_dir}/dir1/baz").exists()
        assert Path(f"overlay/{step_dir}_overlay").exists()

    @pytest.mark.parametrize(
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_overlay_shared_file(self, step, step_dir):
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
        "step,step_dir", [(Step.STAGE, "stage"), (Step.PRIME, "prime")]
    )
    def test_clean_part_shared_file(self, step, step_dir):
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


def _run_step_migration(handler: PartHandler, step: Step) -> None:
    if step > Step.STAGE:
        handler.run_action(Action("", Step.STAGE))
    handler.run_action(Action("", step))


@pytest.mark.usefixtures("new_dir")
class TestPartCleanHandler:
    """Verify step update processing."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, mocker, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part("foo", {"plugin": "dump", "source": "subdir"})
        Path("subdir/bar").mkdir(parents=True)
        Path("subdir/foo.txt").write_text("content")

        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        ovmgr = OverlayManager(
            project_info=info, part_list=[self._part], base_layer_dir=None
        )
        self._part_info = PartInfo(info, self._part)
        self._handler = PartHandler(
            self._part,
            part_info=self._part_info,
            part_list=[self._part],
            overlay_manager=ovmgr,
        )
        # pylint: enable=attribute-defined-outside-init

    @pytest.mark.parametrize(
        "step,test_dir,state_file",
        [
            (Step.PULL, "parts/foo/src", "pull"),
            (Step.BUILD, "parts/foo/install", "build"),
            (Step.STAGE, "stage", "stage"),
            (Step.PRIME, "prime", "prime"),
        ],
    )
    def test_clean_step(self, step, test_dir, state_file):
        self._handler._make_dirs()
        for each_step in step.previous_steps() + [step]:
            self._handler.run_action(Action("foo", each_step))

        assert Path(test_dir, "foo.txt").is_file()
        assert Path(test_dir, "bar").is_dir()
        assert Path(f"parts/foo/state/{state_file}").is_file()

        self._handler.clean_step(step)

        assert Path(test_dir, "foo.txt").is_file() is False
        assert Path(test_dir, "bar").is_dir() is False
        assert Path(f"parts/foo/state/{state_file}").is_file() is False


@pytest.mark.usefixtures("new_dir")
class TestRerunStep:
    """Verify rerun actions."""

    @pytest.mark.parametrize("step", list(Step))
    def test_rerun_action(self, mocker, new_dir, step):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        mock_clean = mocker.patch(
            "craft_parts.executor.part_handler.PartHandler.clean_step"
        )
        mock_callback = mocker.patch("craft_parts.callbacks.run_pre_step")
        mock = mocker.MagicMock()
        mock.attach_mock(mock_clean, "clean_step")
        mock.attach_mock(mock_callback, "run_pre_step")

        handler.run_action(Action("p1", step, ActionType.RERUN))
        calls = [mocker.call.clean_step(step=x) for x in [step] + step.next_steps()]
        calls.append(mocker.call.run_pre_step(mocker.ANY))
        mock.assert_has_calls(calls)


@pytest.mark.usefixtures("new_dir")
class TestPackages:
    """Verify package handling."""

    def test_fetch_stage_packages(self, mocker, new_dir):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result == ["pkg1", "pkg2"]

    def test_fetch_stage_packages_none(self, mocker, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_packages(step_info=step_info)
        assert result is None

    def test_fetch_stage_packages_error(self, mocker, new_dir):
        mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            side_effect=packages.errors.PackageNotFound("pkg1"),
        )

        p1 = Part("p1", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        step_info = StepInfo(part_info, step=Step.PULL)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        with pytest.raises(errors.StagePackageNotFound) as raised:
            handler._fetch_stage_packages(step_info=step_info)
        assert raised.value.part_name == "p1"
        assert raised.value.package_name == "pkg1"

    def test_fetch_stage_snaps(self, mocker, new_dir):
        mock_download_snaps = mocker.patch(
            "craft_parts.packages.snaps.download_snaps",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_snaps()
        assert result == ["word-salad"]
        mock_download_snaps.assert_called_once_with(
            snaps_list=["word-salad"],
            directory=os.path.join(new_dir, "parts/p1/stage_snaps"),
        )

    def test_fetch_stage_snaps_none(self, mocker, new_dir):
        p1 = Part("p1", {"plugin": "nil"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        result = handler._fetch_stage_snaps()
        assert result is None

    def test_unpack_stage_packages(self, mocker, new_dir):
        getpkg = mocker.patch(
            "craft_parts.packages.Repository.fetch_stage_packages",
            return_value=["pkg1", "pkg2"],
        )
        unpack = mocker.patch("craft_parts.packages.Repository.unpack_stage_packages")
        mocker.patch("craft_parts.executor.part_handler.PartHandler._run_step")

        p1 = Part("foo", {"plugin": "nil", "stage-packages": ["pkg1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        state = handler._run_pull(
            StepInfo(part_info, Step.PULL), stdout=None, stderr=None
        )
        getpkg.assert_called_once_with(
            cache_dir=new_dir,
            base=mocker.ANY,
            package_names=["pkg1"],
            stage_packages_path=Path(new_dir / "parts/foo/stage_packages"),
            target_arch=mocker.ANY,
        )

        assert cast(states.PullState, state).assets["stage-packages"] == [
            "pkg1",
            "pkg2",
        ]

        handler._run_build(StepInfo(part_info, Step.BUILD), stdout=None, stderr=None)
        unpack.assert_called_once()

    def test_unpack_stage_snaps(self, mocker, new_dir):
        mock_snap_provision = mocker.patch(
            "craft_parts.sources.snap_source.SnapSource.provision",
        )

        p1 = Part("p1", {"plugin": "nil", "stage-snaps": ["snap1"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )

        Path("parts/p1/stage_snaps").mkdir(parents=True)
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/stage_snaps/snap1.snap").write_text("content")

        handler._unpack_stage_snaps()
        mock_snap_provision.assert_called_once_with(
            new_dir / "parts/p1/install",
            keep=True,
        )

    def test_get_build_packages(self, new_dir):
        p1 = Part(
            "p1", {"plugin": "make", "source": "a.tgz", "build-packages": ["pkg1"]}
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert sorted(handler.build_packages) == ["gcc", "make", "pkg1", "tar"]

    def test_get_build_packages_with_source_type(self, new_dir):
        p1 = Part(
            "p1",
            {
                "plugin": "make",
                "source": "source",
                "source-type": "git",
                "build-packages": ["pkg1"],
            },
        )
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert sorted(handler.build_packages) == ["gcc", "git", "make", "pkg1"]

    def test_get_build_snaps(self, new_dir):
        p1 = Part("p1", {"plugin": "nil", "build-snaps": ["word-salad"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        part_info = PartInfo(info, p1)
        ovmgr = OverlayManager(project_info=info, part_list=[p1], base_layer_dir=None)
        handler = PartHandler(
            p1, part_info=part_info, part_list=[p1], overlay_manager=ovmgr
        )
        assert handler.build_snaps == ["word-salad"]


@pytest.mark.usefixtures("new_dir")
class TestFileFilter:
    """Overlay filter test cases."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        Path("destdir").mkdir()
        Path("destdir/dir1").mkdir()
        Path("destdir/dir1/dir2").mkdir()
        Path("destdir/file1").touch()
        Path("destdir/file2").touch()
        Path("destdir/dir1/file3").touch()
        Path("destdir/file4").symlink_to("file2")
        Path("destdir/dir3").symlink_to("dir1")

    def test_apply_file_filter_empty(self, new_dir):
        destdir = Path("destdir")
        overlay_fileset = filesets.Fileset([])
        files, dirs = filesets.migratable_filesets(overlay_fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_file(self, new_dir):
        destdir = Path("destdir")
        overlay_fileset = filesets.Fileset(["-file1", "-dir1/file3"])
        files, dirs = filesets.migratable_filesets(overlay_fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").exists() is False
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").exists() is False
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_dir(self, new_dir):
        destdir = Path("destdir")
        overlay_fileset = filesets.Fileset(["-dir1", "-dir1/dir2"])
        files, dirs = filesets.migratable_filesets(overlay_fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1").exists() is False
        assert Path("destdir/file4").is_symlink()
        assert Path("destdir/dir3").is_symlink()

    def test_apply_file_filter_remove_symlink(self, new_dir):
        destdir = Path("destdir")
        overlay_fileset = filesets.Fileset(["-file4", "-dir3"])
        files, dirs = filesets.migratable_filesets(overlay_fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").is_file()
        assert Path("destdir/file2").is_file()
        assert Path("destdir/dir1/dir2").is_dir()
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").exists() is False
        assert Path("destdir/dir3").exists() is False

    def test_apply_file_filter_keep_file(self, new_dir):
        destdir = Path("destdir")
        overlay_fileset = filesets.Fileset(["dir1/file3"])
        files, dirs = filesets.migratable_filesets(overlay_fileset, str(destdir))
        part_handler._apply_file_filter(
            filter_files=files, filter_dirs=dirs, destdir=destdir
        )

        assert Path("destdir/file1").exists() is False
        assert Path("destdir/file2").exists() is False
        assert Path("destdir/dir1/dir2").exists() is False
        assert Path("destdir/dir1/file3").is_file()
        assert Path("destdir/file4").exists() is False
        assert Path("destdir/dir3").exists() is False


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify helper functions."""

    def test_remove_file(self):
        test_file = Path("foo.txt")
        test_file.write_text("content")
        assert test_file.exists()

        part_handler._remove(test_file)
        assert test_file.is_file() is False

    def test_remove_symlink(self):
        test_link = Path("foo")
        test_link.symlink_to("target")
        assert test_link.is_symlink()

        part_handler._remove(test_link)
        assert test_link.exists() is False

    def test_remove_dir(self):
        test_dir = Path("bar")
        test_dir.mkdir()
        assert test_dir.is_dir()

        part_handler._remove(test_dir)
        assert test_dir.exists() is False

    def test_remove_non_existent(self):
        # this should not raise and exception
        part_handler._remove(Path("not_here"))

    @pytest.mark.parametrize("step", list(Step))
    def test_parts_with_overlay_in_step(self, step):
        p1 = Part("p1", {"plugin": "nil"})
        p2 = Part("p2", {"plugin": "nil", "overlay-script": "ls"})
        p3 = Part("p3", {"plugin": "nil", "overlay-packages": ["pkg1"]})
        p4 = Part("p4", {"plugin": "nil", "overlay": ["/etc"]})

        res = part_handler._parts_with_overlay_in_step(step, part_list=[p1, p2, p3, p4])
        assert res == []

        for part in [p1, p2, p3, p4]:
            state_path = states.get_step_state_path(part, step)
            state_path.parent.mkdir(parents=True)
            state_path.touch()

        res = part_handler._parts_with_overlay_in_step(step, part_list=[p1, p2, p3, p4])
        assert res == [p2, p3, p4]
