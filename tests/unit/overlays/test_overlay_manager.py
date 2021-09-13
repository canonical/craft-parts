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

from pathlib import Path

import pytest

from craft_parts.infos import ProjectInfo
from craft_parts.overlays import OverlayManager
from craft_parts.overlays.overlay_fs import OverlayFS
from craft_parts.parts import Part


class TestLayerMounting:
    """Verify overlayfs mounting and unmounting ."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        # pylint: disable=attribute-defined-outside-init
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        self.p1 = Part("p1", {"plugin": "nil"})
        self.p2 = Part("p2", {"plugin": "nil"})
        base_layer_dir = Path("base_dir")
        base_layer_dir.mkdir()
        self.om = OverlayManager(
            project_info=info,
            part_list=[self.p1, self.p2],
            base_layer_dir=base_layer_dir,
        )
        # pylint: enable=attribute-defined-outside-init

    def test_mount_layer(self, new_dir, mocker):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self.om.mount_layer(self.p2)
        mock_mount.assert_called_with(
            "overlay",
            str(new_dir / "overlay/overlay"),
            "-toverlay",
            f"-olowerdir={new_dir}/parts/p1/layer:base_dir,"
            f"upperdir={new_dir}/parts/p2/layer,"
            f"workdir={new_dir}/overlay/work",
        )

    def test_mount_layer_single_part(self, new_dir, mocker):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self.om.mount_layer(self.p1)
        mock_mount.assert_called_with(
            "overlay",
            str(new_dir / "overlay/overlay"),
            "-toverlay",
            f"-olowerdir=base_dir,upperdir={new_dir}/parts/p1/layer,"
            f"workdir={new_dir}/overlay/work",
        )

    def test_mount_layer_pkg_cache(self, new_dir, mocker):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self.om.mount_layer(self.p1, pkg_cache=True)
        mock_mount.assert_called_with(
            "overlay",
            str(new_dir / "overlay/overlay"),
            "-toverlay",
            f"-olowerdir={new_dir}/overlay/packages:base_dir,"
            f"upperdir={new_dir}/parts/p1/layer,"
            f"workdir={new_dir}/overlay/work",
        )

    def test_mount_layer_no_base(self, new_dir, mocker):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        overlay_manager = OverlayManager(
            project_info=info,
            part_list=[self.p1, self.p2],
            base_layer_dir=None,
        )

        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")

        with pytest.raises(RuntimeError) as raised:
            overlay_manager.mount_layer(self.p1)

        assert str(raised.value) == "request to mount overlay without a base layer"
        mock_mount.assert_not_called()

    def test_mount_pkg_cache(self, new_dir, mocker):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        self.om.mount_pkg_cache()
        mock_mount.assert_called_with(
            "overlay",
            str(new_dir / "overlay/overlay"),
            "-toverlay",
            f"-olowerdir=base_dir,upperdir={new_dir}/overlay/packages,"
            f"workdir={new_dir}/overlay/work",
        )

    def test_mount_pkg_cache_no_base(self, new_dir, mocker):
        info = ProjectInfo(application_name="test", cache_dir=new_dir)
        overlay_manager = OverlayManager(
            project_info=info,
            part_list=[self.p1, self.p2],
            base_layer_dir=None,
        )

        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")

        with pytest.raises(RuntimeError) as raised:
            overlay_manager.mount_pkg_cache()

        assert str(raised.value) == (
            "request to mount the overlay package cache without a base layer"
        )
        mock_mount.assert_not_called()

    def test_unmount(self, mocker):
        mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        self.om._overlay_fs = OverlayFS(
            lower_dirs=[Path("/lower_dir")],
            upper_dir=Path("/upper_dir"),
            work_dir=Path("/work_dir"),
        )
        self.om._overlay_fs.mount(Path("/mnt"))

        self.om.unmount()
        mock_umount.assert_called_with("/mnt")

    def test_unmount_not_mounted(self, mocker):
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        self.om.unmount()
        mock_umount.assert_not_called()

    def test_mkdirs(self, new_dir):
        self.om.mkdirs()
        Path("overlay/overlay").is_dir()
        Path("overlay/packages").is_dir()
        Path("overlay/work").is_dir()
