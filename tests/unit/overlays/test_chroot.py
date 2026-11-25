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
import subprocess
from pathlib import Path, PosixPath
from unittest.mock import ANY, call

import pytest
from craft_parts.overlays import chroot

_FORK_CTX = multiprocessing.get_context("fork")


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


@pytest.mark.usefixtures("new_dir")
class TestChroot:
    """Fork process and execute in chroot."""

    def test_chroot(self, mocker, new_dir, mock_chroot):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(_FORK_CTX, "Process")
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
            call(Path("/etc/resolv.conf"), new_root / "etc" / "resolv.conf", "--bind"),
            call(Path("proc"), new_root / "proc", "-tproc"),
            call(Path("sysfs"), new_root / "sys", "-tsysfs"),
            call(Path("/dev"), new_root / "dev", "--rbind", "--make-rprivate"),
            call(new_root / "dev", None, "--make-rprivate"),
            call(new_root / "sys", None, "--make-rprivate"),
            call(new_root / "proc", None, "--make-rprivate"),
            call(new_root / "etc" / "resolv.conf", None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(new_root / "dev", "--recursive", "--lazy"),
            call(new_root / "sys", "--recursive"),
            call(new_root / "proc", "--recursive"),
            call(new_root / "etc" / "resolv.conf", "--recursive"),
        ]

    def test_chroot_no_mountpoints(self, mocker, new_dir):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(_FORK_CTX, "Process")
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

        spy_process = mocker.spy(_FORK_CTX, "Process")
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
            call(Path("/etc/resolv.conf"), new_root / "etc" / "resolv.conf", "--bind"),
            call(new_root / "etc" / "resolv.conf", None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(new_root / "etc" / "resolv.conf", "--recursive"),
        ]

    def test_chroot_no_resolv_conf(self, mocker, new_dir):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        spy_process = mocker.spy(_FORK_CTX, "Process")
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
            call(Path("/etc/resolv.conf"), new_root / "etc" / "resolv.conf", "--bind"),
            call(new_root / "etc" / "resolv.conf", None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(new_root / "etc" / "resolv.conf", "--recursive"),
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
        host_apt_configs = []

        def mount(source, target, *args):
            if (
                target == new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates"
                and args == ("--bind",)
            ):
                host_apt_configs.append((source, source.read_text()))

        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount", side_effect=mount)
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")
        mock_copytree = mocker.patch("shutil.copytree")

        spy_process = mocker.spy(_FORK_CTX, "Process")
        new_root = Path(new_dir, "dir1")

        # this runs in the child process
        Path("dir1").mkdir()
        for subdir in [
            "etc",
            "etc/apt",
            "etc/apt/apt.conf.d",
            "proc",
            "sys",
            "dev",
            "dev/shm",
        ]:
            Path(new_root, subdir).mkdir()

        chroot.chroot(new_root, target_func, "content", use_host_sources=True)

        assert len(host_apt_configs) == 1
        host_apt_conf, contents = host_apt_configs[0]
        assert contents == (
            'Acquire::https::CaInfo "/etc/apt/craft-parts-ca-certificates.crt";\n'
        )
        assert not host_apt_conf.is_relative_to(new_root)
        assert not host_apt_conf.exists()
        assert Path("dir1/foo.txt").read_text() == "content"
        assert spy_process.mock_calls == [
            call(
                target=chroot._runner,
                args=(new_root, ANY, target_func, ("content",), {}),
            )
        ]
        assert mock_mount.mock_calls == [
            call(
                PosixPath("/etc/resolv.conf"),
                PosixPath(f"{new_root}/etc/resolv.conf"),
                "--bind",
            ),
            call(PosixPath("proc"), PosixPath(f"{new_root}/proc"), "-tproc"),
            call(PosixPath("sysfs"), PosixPath(f"{new_root}/sys"), "-tsysfs"),
            call(
                PosixPath("/dev"),
                PosixPath(f"{new_root}/dev"),
                "--rbind",
                "--make-rprivate",
            ),
            call(PosixPath("/etc/apt"), PosixPath(f"{new_root}/etc/apt"), "-ttmpfs"),
            call(
                PosixPath("/etc/ssl/certs/ca-certificates.crt"),
                new_root / "etc/apt/craft-parts-ca-certificates.crt",
                "--bind",
            ),
            call(
                new_root / "etc/apt/craft-parts-ca-certificates.crt",
                None,
                "-o",
                "remount,bind,ro",
            ),
            call(
                host_apt_conf,
                new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates",
                "--bind",
            ),
            call(
                new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates",
                None,
                "-o",
                "remount,bind,ro",
            ),
            call(
                new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates",
                None,
                "--make-rprivate",
            ),
            call(PosixPath(f"{new_root}/dev"), None, "--make-rprivate"),
            call(PosixPath(f"{new_root}/sys"), None, "--make-rprivate"),
            call(PosixPath(f"{new_root}/proc"), None, "--make-rprivate"),
            call(PosixPath(f"{new_root}/etc/resolv.conf"), None, "--make-rprivate"),
            call(
                new_root / "etc/apt/craft-parts-ca-certificates.crt",
                None,
                "--make-rprivate",
            ),
            call(PosixPath(f"{new_root}/etc/apt"), None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(
                new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates",
                "--recursive",
            ),
            call(PosixPath(f"{new_root}/dev"), "--recursive", "--lazy"),
            call(PosixPath(f"{new_root}/sys"), "--recursive"),
            call(PosixPath(f"{new_root}/proc"), "--recursive"),
            call(PosixPath(f"{new_root}/etc/resolv.conf"), "--recursive"),
            call(
                new_root / "etc/apt/craft-parts-ca-certificates.crt",
                "--recursive",
            ),
            call(PosixPath(f"{new_root}/etc/apt"), "--recursive"),
        ]

        # Check that apt sources were copied to the chroot
        assert mock_copytree.mock_calls == [
            call(
                PosixPath("/etc/apt"),
                PosixPath(f"{new_root}/etc/apt"),
                dirs_exist_ok=True,
            )
        ]

    @pytest.mark.parametrize("fail_configuration_mount", [True, False])
    def test_chroot_host_sources_failure_cleans_ca_mount(
        self, mocker, new_dir, mock_chroot, fail_configuration_mount
    ):
        new_root = Path(new_dir, "root")
        (new_root / "etc/apt/apt.conf.d").mkdir(parents=True)
        apt_conf_target = new_root / "etc/apt/apt.conf.d/99craft-parts-ca-certificates"
        host_apt_configs = []

        def mount(source, target, *args):
            if target == apt_conf_target and args == ("--bind",):
                host_apt_configs.append(source)
            if fail_configuration_mount and source == apt_conf_target and "-o" in args:
                raise subprocess.CalledProcessError(32, ["mount"])

        def umount(target, *args):
            if target == apt_conf_target:
                assert host_apt_configs[0].exists()

        mocker.patch("craft_parts.utils.os_utils.mount", side_effect=mount)
        mock_umount = mocker.patch(
            "craft_parts.utils.os_utils.umount", side_effect=umount
        )
        mocker.patch("shutil.copytree")

        if fail_configuration_mount:
            expected_error = subprocess.CalledProcessError
            message = "mount"
        else:
            expected_error = chroot.errors.OverlayChrootExecutionError
            message = "bummer"

        with pytest.raises(expected_error, match=message):
            chroot.chroot(new_root, target_func_error, "content", use_host_sources=True)

        assert len(host_apt_configs) == 1
        assert not host_apt_configs[0].exists()
        assert mock_umount.mock_calls[0] == call(apt_conf_target, "--recursive")
        assert mock_umount.mock_calls[-2:] == [
            call(new_root / "etc/apt/craft-parts-ca-certificates.crt", "--recursive"),
            call(new_root / "etc/apt", "--recursive"),
        ]

    def test_chroot_additional_bind_mounts(self, mocker, new_dir, mock_chroot):
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")
        new_dir = Path(new_dir)
        new_root = new_dir / "root"
        writable = new_dir / "writable"
        read_only = new_dir / "read-only"
        new_root.mkdir()
        writable.mkdir()
        read_only.mkdir()

        chroot.chroot(
            new_root,
            target_func,
            "content",
            bind_mounts=[
                chroot.BindMount(writable, writable),
                chroot.BindMount(read_only, read_only, read_only=True),
            ],
        )

        writable_target = new_root / str(writable).lstrip("/")
        read_only_target = new_root / str(read_only).lstrip("/")
        assert mock_mount.mock_calls == [
            call(writable, writable_target, "--bind"),
            call(read_only, read_only_target, "--bind"),
            call(read_only_target, None, "-o", "remount,bind,ro"),
            call(read_only_target, None, "--make-rprivate"),
            call(writable_target, None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(read_only_target, "--recursive"),
            call(writable_target, "--recursive"),
        ]

    def test_chroot_additional_mount_setup_failure_cleans_previous_mount(
        self, mocker, new_dir
    ):
        new_dir = Path(new_dir)
        new_root = new_dir / "root"
        first = new_dir / "first"
        second = new_dir / "second"
        new_root.mkdir()
        first.mkdir()
        second.mkdir()

        def mount(source, target, *args):
            if source == second:
                raise subprocess.CalledProcessError(32, ["mount"])

        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount", side_effect=mount)
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        with pytest.raises(subprocess.CalledProcessError):
            chroot.chroot(
                new_root,
                target_func,
                "content",
                bind_mounts=[
                    chroot.BindMount(first, first),
                    chroot.BindMount(second, second),
                ],
            )

        first_target = new_root / str(first).lstrip("/")
        second_target = new_root / str(second).lstrip("/")
        assert mock_mount.mock_calls == [
            call(first, first_target, "--bind"),
            call(second, second_target, "--bind"),
            call(first_target, None, "--make-rprivate"),
        ]
        mock_umount.assert_called_once_with(first_target, "--recursive")

    def test_read_only_bind_mount_rolls_back_failed_remount(self, mocker, new_dir):
        new_dir = Path(new_dir)
        new_root = new_dir / "root"
        source = new_dir / "source"
        new_root.mkdir()
        source.mkdir()
        mount = chroot._ReadOnlyBindMount(source, source, skip_missing=False)
        mock_mount = mocker.patch(
            "craft_parts.utils.os_utils.mount",
            side_effect=[None, subprocess.CalledProcessError(32, ["mount"])],
        )
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        with pytest.raises(subprocess.CalledProcessError):
            mount.mount_to(new_root)

        target = new_root / str(source).lstrip("/")
        assert mock_mount.mock_calls == [
            call(source, target, "--bind"),
            call(target, None, "-o", "remount,bind,ro"),
        ]
        mock_umount.assert_called_once_with(target, "--recursive")
        assert mount._mounted is False

    def test_chroot_target_failure_cleans_additional_mount(
        self, mocker, new_dir, mock_chroot
    ):
        new_dir = Path(new_dir)
        new_root = new_dir / "root"
        source = new_dir / "source"
        new_root.mkdir()
        source.mkdir()
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        with pytest.raises(chroot.errors.OverlayChrootExecutionError, match="bummer"):
            chroot.chroot(
                new_root,
                target_func_error,
                "content",
                bind_mounts=[chroot.BindMount(source, source)],
            )

        target = new_root / str(source).lstrip("/")
        assert mock_mount.mock_calls == [
            call(source, target, "--bind"),
            call(target, None, "--make-rprivate"),
        ]
        mock_umount.assert_called_once_with(target, "--recursive")

    def test_bind_mount_can_be_reused(self, mocker, new_dir):
        new_dir = Path(new_dir)
        new_root = new_dir / "root"
        source = new_dir / "source"
        new_root.mkdir()
        source.mkdir()
        mount = chroot._BindMount(source, source, skip_missing=False)
        mock_mount = mocker.patch("craft_parts.utils.os_utils.mount")
        mock_umount = mocker.patch("craft_parts.utils.os_utils.umount")

        mount.mount_to(new_root)
        mount.unmount_from(new_root)
        mount.mount_to(new_root)
        mount.unmount_from(new_root)

        target = new_root / str(source).lstrip("/")
        assert mock_mount.mock_calls == [
            call(source, target, "--bind"),
            call(target, None, "--make-rprivate"),
            call(source, target, "--bind"),
            call(target, None, "--make-rprivate"),
        ]
        assert mock_umount.mock_calls == [
            call(target, "--recursive"),
            call(target, "--recursive"),
        ]
        assert mount._mounted is False
