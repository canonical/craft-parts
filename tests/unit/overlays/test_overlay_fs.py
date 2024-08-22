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

import os
from pathlib import Path
from subprocess import CalledProcessError

import pytest
from craft_parts.overlays import errors, overlay_fs


class TestOverlayFS:
    """Mount and unmount an overlayfs."""

    @staticmethod
    def _make_overlay_fs(lower: list[Path]) -> overlay_fs.OverlayFS:
        return overlay_fs.OverlayFS(
            lower_dirs=lower,
            upper_dir=Path("/upper"),
            work_dir=Path("/work"),
        )

    def test_mount_single_lower(self, mocker):
        mock_mount_overlayfs = mocker.patch(
            "craft_parts.utils.os_utils.mount_overlayfs"
        )

        ovfs = self._make_overlay_fs([Path("/lower")])
        ovfs.mount(Path("/mountpoint"))
        mock_mount_overlayfs.assert_called_once_with(
            "/mountpoint",
            "-olowerdir=/lower,upperdir=/upper,workdir=/work",
        )

    def test_mount_multiple_lower(self, mocker):
        mock_mount_overlayfs = mocker.patch(
            "craft_parts.utils.os_utils.mount_overlayfs"
        )

        ovfs = self._make_overlay_fs([Path("/lower1"), Path("/lower2")])
        ovfs.mount(Path("/mountpoint"))
        mock_mount_overlayfs.assert_called_once_with(
            "/mountpoint",
            "-olowerdir=/lower1:/lower2,upperdir=/upper,workdir=/work",
        )

    def test_mount_error(self, mocker):
        mocker.patch(
            "craft_parts.utils.os_utils.mount_overlayfs",
            side_effect=CalledProcessError(cmd=["some", "command"], returncode=42),
        )

        ovfs = self._make_overlay_fs([Path("/lower")])
        with pytest.raises(errors.OverlayMountError) as err:
            ovfs.mount(Path("/mountpoint"))
        assert err.value.mountpoint == "/mountpoint"
        assert (
            err.value.message
            == "Command '['some', 'command']' returned non-zero exit status 42."
        )

    def test_unmount(self, mocker):
        mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        ovfs = self._make_overlay_fs([Path("/lower")])
        ovfs.mount(Path("/mountpoint"))
        ovfs.unmount()
        mock_umount.assert_called_once_with("/mountpoint")

    def test_unmount_not_mounted(self, mocker):
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        ovfs = self._make_overlay_fs([Path("/lower")])
        ovfs.unmount()
        mock_umount.assert_not_called()

    def test_unmount_multiple(self, mocker):
        mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        ovfs = self._make_overlay_fs([Path("/lower")])
        ovfs.mount(Path("/mountpoint"))
        ovfs.unmount()
        ovfs.unmount()
        ovfs.unmount()
        mock_umount.assert_called_once_with("/mountpoint")

    def test_unmount_error(self, mocker):
        mocker.patch("craft_parts.utils.os_utils.mount_overlayfs")
        mocker.patch(
            "craft_parts.utils.os_utils.umount",
            side_effect=CalledProcessError(cmd=["some", "command"], returncode=42),
        )

        ovfs = self._make_overlay_fs([Path("/lower")])
        ovfs.mount(Path("/mountpoint"))

        with pytest.raises(errors.OverlayUnmountError) as err:
            ovfs.unmount()
        assert err.value.mountpoint == "/mountpoint"
        assert (
            err.value.message
            == "Command '['some', 'command']' returned non-zero exit status 42."
        )


@pytest.mark.usefixtures("new_dir")
class TestHelpers:
    """Verify overlayfs utility functions."""

    @pytest.mark.parametrize(
        ("is_chardev", "is_symlink", "rdev", "result"),
        [
            (True, False, os.makedev(0, 0), True),
            (True, True, os.makedev(0, 0), False),
            (False, False, os.makedev(0, 0), False),
            (True, False, os.makedev(1, 0), False),
            (True, False, os.makedev(0, 1), False),
        ],
    )
    def test_is_whiteout_file(self, mocker, is_chardev, is_symlink, rdev, result):
        fake_stats = mocker.Mock()
        fake_stats.st_rdev = rdev
        mocker.patch("os.stat", return_value=fake_stats)
        mocker.patch("pathlib.Path.is_char_device", return_value=is_chardev)

        if is_symlink:
            Path("target").touch()
            Path("whiteout_file").symlink_to("target")
        else:
            Path("whiteout_file").touch()

        mocker.patch("pathlib.Path.is_symlink", return_value=is_symlink)

        assert overlay_fs.is_whiteout_file(Path("whiteout_file")) == result

    def test_not_whiteout_file(self):
        Path("regular_file").touch()
        assert overlay_fs.is_whiteout_file(Path("regular_file")) is False

    def test_whiteout_file_missing(self):
        assert Path("missing_file").exists() is False
        assert overlay_fs.is_whiteout_file(Path("missing_file")) is False

    @pytest.mark.parametrize(
        ("is_dir", "is_symlink", "attr", "result"),
        [
            (True, False, b"y", True),
            (True, True, b"y", False),
            (False, True, b"y", False),
            (True, False, b"n", False),
        ],
    )
    def test_is_opaque_dir(self, mocker, is_dir, is_symlink, attr, result):
        if is_symlink:
            if is_dir:
                Path("target").mkdir()
            else:
                Path("target").touch()

            Path("opaque_dir").symlink_to("target")
        elif is_dir:
            Path("opaque_dir").mkdir()
        else:
            Path("opaque_dir").touch()

        mocker.patch("os.getxattr", return_value=attr)

        assert overlay_fs.is_opaque_dir(Path("opaque_dir")) == result

    def test_opaque_dir_missing(self):
        assert Path("missing").exists() is False
        assert overlay_fs.is_opaque_dir(Path("missing")) is False
