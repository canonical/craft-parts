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

import multiprocessing
from pathlib import Path, PosixPath
from unittest.mock import ANY, call

import pytest
from craft_parts.overlays import chroot


def target_func(content: str) -> int:
    Path("foo.txt").write_text(content)
    return 1337


def target_func_error(content: str) -> int:
    raise RuntimeError("bummer")


class FakeConn:
    """Fake connection."""

    def __init__(self):
        self.sent = None

    def send(self, data):
        self.sent = data


@pytest.fixture
def fake_conn():
    return FakeConn()


@pytest.mark.usefixtures("new_dir", "multiprocessing_fork")
class TestChroot:
    """Fork process and execute in chroot."""

    def test_chroot(self, mocker, new_dir, mock_chroot):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(multiprocessing, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        Path("dir1").mkdir()
        for subdir in ["etc", "proc", "sys", "dev", "dev/shm"]:
            Path(new_root, subdir).mkdir()

        chroot.chroot(new_root, target_func, "content")

        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == [
            call("/etc/resolv.conf", f"{new_root}/etc/resolv.conf", "--bind"),
            call("proc", f"{new_root}/proc", "-tproc"),
            call("sysfs", f"{new_root}/sys", "-tsysfs"),
            call("/dev", f"{new_root}/dev", "--rbind", "--make-rprivate"),
            call(f"{new_root}/dev", "--make-rprivate"),
            call(f"{new_root}/sys", "--make-rprivate"),
            call(f"{new_root}/proc", "--make-rprivate"),
            call(f"{new_root}/etc/resolv.conf", "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(f"{new_root}/dev", "--recursive", "--lazy"),
            call(f"{new_root}/sys", "--recursive"),
            call(f"{new_root}/proc", "--recursive"),
            call(f"{new_root}/etc/resolv.conf", "--recursive"),
        ]

    def test_chroot_no_mountpoints(self, mocker, new_dir):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(multiprocessing, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        mocker.patch("os.chroot")

        Path("dir1").mkdir()
        chroot.chroot(new_root, target_func, "content")

        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == []
        assert mock_umount.mock_calls == []

    def test_chroot_symlinked_resolv_conf(self, mocker, new_dir):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(multiprocessing, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        mocker.patch("os.chroot")

        Path("dir1").mkdir()
        Path("dir1/etc").mkdir()
        Path("dir1/etc/resolv.conf").symlink_to("whatever")
        chroot.chroot(new_root, target_func, "content")

        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == [
            call("/etc/resolv.conf", f"{new_root}/etc/resolv.conf", "--bind"),
            call(f"{new_root}/etc/resolv.conf", "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(f"{new_root}/etc/resolv.conf", "--recursive"),
        ]

    def test_chroot_no_resolv_conf(self, mocker, new_dir):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(multiprocessing, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        mocker.patch("os.chroot")

        Path("dir1").mkdir()
        Path("dir1/etc").mkdir()
        chroot.chroot(new_root, target_func, "content")

        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == [
            call("/etc/resolv.conf", f"{new_root}/etc/resolv.conf", "--bind"),
            call(f"{new_root}/etc/resolv.conf", "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(f"{new_root}/etc/resolv.conf", "--recursive"),
        ]

    def test_runner(self, fake_conn, mock_chdir, mock_chroot):
        chroot._runner(Path("/some/path"), fake_conn, target_func, ("func arg",), {})

        assert Path("foo.txt").read_text() == "func arg"
        assert mock_chdir.mock_calls == [call(Path("/some/path"))]
        assert mock_chroot.mock_calls == [call(Path("/some/path"))]
        assert fake_conn.sent == (1337, None)

    def test_runner_error(self, fake_conn, mock_chdir, mock_chroot):
        chroot._runner(
            Path("/some/path"), fake_conn, target_func_error, ("func arg",), {}
        )

        assert mock_chdir.mock_calls == [call(Path("/some/path"))]
        assert mock_chroot.mock_calls == [call(Path("/some/path"))]
        assert fake_conn.sent[0] is None
        assert isinstance(fake_conn.sent[1], str)
        assert str(fake_conn.sent[1]) == "bummer"

    def test_chroot_use_host_sources(self, mocker, new_dir, mock_chroot):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")
        mock_copytree = mocker.patch("shutil.copytree")

        spy_process = mocker.spy(multiprocessing, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        Path("dir1").mkdir()
        for subdir in ["etc", "proc", "sys", "dev", "dev/shm"]:
            Path(new_root, subdir).mkdir()

        chroot.chroot(new_root, target_func, "content", use_host_sources=True)

        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == [
            call("/etc/resolv.conf", f"{new_root}/etc/resolv.conf", "--bind"),
            call("proc", f"{new_root}/proc", "-tproc"),
            call("sysfs", f"{new_root}/sys", "-tsysfs"),
            call("/dev", f"{new_root}/dev", "--rbind", "--make-rprivate"),
            call("/etc/apt", f"{new_root}/etc/apt", "-ttmpfs"),
            call(
                "/usr/share/ca-certificates",
                f"{new_root}/usr/share/ca-certificates",
                "--bind",
            ),
            call("/etc/ssl/certs", f"{new_root}/etc/ssl/certs", "--bind"),
            call(
                "/etc/ca-certificates.conf",
                f"{new_root}/etc/ca-certificates.conf",
                "--bind",
            ),
            call(f"{new_root}/dev", "--make-rprivate"),
            call(f"{new_root}/sys", "--make-rprivate"),
            call(f"{new_root}/proc", "--make-rprivate"),
            call(f"{new_root}/etc/resolv.conf", "--make-rprivate"),
            call(f"{new_root}/etc/ca-certificates.conf", "--make-rprivate"),
            call(f"{new_root}/etc/ssl/certs", "--make-rprivate"),
            call(f"{new_root}/usr/share/ca-certificates", "--make-rprivate"),
            call(f"{new_root}/etc/apt", "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(f"{new_root}/dev", "--recursive", "--lazy"),
            call(f"{new_root}/sys", "--recursive"),
            call(f"{new_root}/proc", "--recursive"),
            call(f"{new_root}/etc/resolv.conf", "--recursive"),
            call(f"{new_root}/etc/ca-certificates.conf", "--recursive"),
            call(f"{new_root}/etc/ssl/certs", "--recursive"),
            call(f"{new_root}/usr/share/ca-certificates", "--recursive"),
            call(f"{new_root}/etc/apt", "--recursive"),
        ]

        # Check that apt sources were copied to the chroot
        assert mock_copytree.mock_calls == [
            call(
                PosixPath("/etc/apt"),
                PosixPath(f"{new_root}/etc/apt"),
                dirs_exist_ok=True,
            )
        ]
