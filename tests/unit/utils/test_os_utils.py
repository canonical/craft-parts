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

import itertools
import os
import subprocess
import textwrap
from pathlib import Path
from unittest import mock
from unittest.mock import call

import pytest
from craft_parts import errors
from craft_parts.utils import os_utils


@pytest.fixture
def fake_check_output(mocker):
    return mocker.patch("subprocess.check_output")


class TestTimedWriter:
    """Check if minimum interval ensured between writes."""

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_no_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # a long time has passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time + 1
        os_utils.TimedWriter.write_text(Path("foo"), "content")
        mock_sleep.assert_not_called()

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_full_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # no time passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time
        os_utils.TimedWriter.write_text(Path("bar"), "content")
        mock_sleep.assert_called_with(pytest.approx(0.02, 0.00001))

    @pytest.mark.usefixtures("new_dir")
    def test_timed_write_partial_wait(self, mocker):
        mock_time = mocker.patch("time.time")
        mock_sleep = mocker.patch("time.sleep")

        # some time passed since the last write
        mock_time.return_value = os_utils.TimedWriter._last_write_time + 0.005
        os_utils.TimedWriter.write_text(Path("baz"), "content")
        mock_sleep.assert_called_with(pytest.approx(0.015, 0.00001))


class TestSystemInfo:
    """Verify retrieval of system information."""

    def test_get_system_info(self, fake_check_output):
        fake_check_output.return_value = (
            b"Linux 5.4.0-70-generic #78-Ubuntu SMP Fri Mar 19 13:29:52 "
            b"UTC 2021 x86_64 x86_64 x86_64 GNU/Linux\n"
        )

        res = os_utils.get_system_info()
        assert res == (
            "Linux 5.4.0-70-generic #78-Ubuntu SMP Fri Mar 19 13:29:52 "
            "UTC 2021 x86_64 x86_64 x86_64 GNU/Linux"
        )
        fake_check_output.assert_called_once_with(
            [
                "uname",
                "--kernel-name",
                "--kernel-release",
                "--kernel-version",
                "--machine",
                "--processor",
                "--hardware-platform",
                "--operating-system",
            ]
        )


class TestGetPaths:
    """Verify functions that get lists of system paths."""

    def test_get_bin_paths_null(self, new_dir):
        x = os_utils.get_bin_paths(root=new_dir)
        assert x == []

    def test_get_bin_paths_exist(self, new_dir):
        for directory in ["usr/sbin", "usr/bin", "sbin", "bin", "other"]:
            Path(directory).mkdir(parents=True)

        x = os_utils.get_bin_paths(root=new_dir)

        assert x == [
            f"{new_dir}/usr/sbin",
            f"{new_dir}/usr/bin",
            f"{new_dir}/sbin",
            f"{new_dir}/bin",
        ]

    def test_get_bin_paths_not_exist(self):
        x = os_utils.get_bin_paths(root=Path("/invalid"), existing_only=False)
        assert x == [
            "/invalid/usr/sbin",
            "/invalid/usr/bin",
            "/invalid/sbin",
            "/invalid/bin",
        ]

    def test_get_include_paths_null(self):
        x = os_utils.get_include_paths(
            root=Path("/invalid"), arch_triplet="my-arch-triplet"
        )
        assert x == []

    def test_get_include_paths(self, new_dir):
        for directory in [
            "include",
            "usr/include",
            "include/my-arch-triplet",
            "usr/include/my-arch-triplet",
            "something/else",
        ]:
            Path(directory).mkdir(parents=True)

        x = os_utils.get_include_paths(root=new_dir, arch_triplet="my-arch-triplet")
        assert x == [
            f"{new_dir}/include",
            f"{new_dir}/usr/include",
            f"{new_dir}/include/my-arch-triplet",
            f"{new_dir}/usr/include/my-arch-triplet",
        ]

    def test_get_library_paths_null(self):
        x = os_utils.get_library_paths(
            root=Path("/invalid"), arch_triplet="my-arch-triplet"
        )
        assert x == []

    def test_get_library_paths_exist(self, new_dir):
        for directory in [
            "lib",
            "usr/lib",
            "lib/my-arch-triplet",
            "usr/lib/my-arch-triplet",
            "other",
        ]:
            Path(directory).mkdir(parents=True)

        x = os_utils.get_library_paths(root=new_dir, arch_triplet="my-arch-triplet")

        assert x == [
            f"{new_dir}/lib",
            f"{new_dir}/usr/lib",
            f"{new_dir}/lib/my-arch-triplet",
            f"{new_dir}/usr/lib/my-arch-triplet",
        ]

    def test_get_library_paths_not_exist(self):
        x = os_utils.get_library_paths(
            root=Path("/invalid"), arch_triplet="my-arch-triplet", existing_only=False
        )
        assert x == [
            "/invalid/lib",
            "/invalid/usr/lib",
            "/invalid/lib/my-arch-triplet",
            "/invalid/usr/lib/my-arch-triplet",
        ]

    def test_get_pkg_config_paths_null(self):
        x = os_utils.get_pkg_config_paths(
            root=Path("/invalid"), arch_triplet="my-arch-triplet"
        )
        assert x == []

    def test_get_pkg_config_paths(self, new_dir):
        for directory in [
            "lib/pkgconfig",
            "lib/my-arch-triplet/pkgconfig",
            "usr/lib/pkgconfig",
            "usr/lib/my-arch-triplet/pkgconfig",
            "usr/share/pkgconfig",
            "usr/local/lib/pkgconfig",
            "usr/local/lib/my-arch-triplet/pkgconfig",
            "usr/local/share/pkgconfig",
            "something/else",
        ]:
            Path(directory).mkdir(parents=True)

        x = os_utils.get_pkg_config_paths(root=new_dir, arch_triplet="my-arch-triplet")
        assert x == [
            f"{new_dir}/lib/pkgconfig",
            f"{new_dir}/lib/my-arch-triplet/pkgconfig",
            f"{new_dir}/usr/lib/pkgconfig",
            f"{new_dir}/usr/lib/my-arch-triplet/pkgconfig",
            f"{new_dir}/usr/share/pkgconfig",
            f"{new_dir}/usr/local/lib/pkgconfig",
            f"{new_dir}/usr/local/lib/my-arch-triplet/pkgconfig",
            f"{new_dir}/usr/local/share/pkgconfig",
        ]


class TestTerminal:
    """Tests for terminal-related utilities."""

    @pytest.mark.parametrize(
        ("isatty", "term", "result"),
        [
            (False, "xterm", True),
            (False, "dumb", True),
            (True, "xterm", False),
            (True, "dumb", True),
        ],
    )
    def test_is_dumb_terminal(self, mocker, isatty, term, result):
        mocker.patch("os.isatty", return_value=isatty)
        mocker.patch.dict(os.environ, {"TERM": term})

        assert os_utils.is_dumb_terminal() == result


@pytest.mark.usefixtures("new_dir")
class TestOsRelease:
    """Verify os-release data retrieval."""

    def _write_os_release(self, contents) -> str:
        path = "os-release"
        with open(path, "w") as f:
            f.write(contents)
        return path

    def test_blank_lines(self):
        release = os_utils.OsRelease(
            os_release_file=self._write_os_release(
                textwrap.dedent(
                    """\
                NAME="Arch Linux"

                PRETTY_NAME="Arch Linux"
                ID=arch
                ID_LIKE=archlinux
                VERSION_ID="foo"
                VERSION_CODENAME="bar"

            """
                )
            )
        )

        assert release.id() == "arch"
        assert release.name() == "Arch Linux"
        assert release.version_id() == "foo"

    def test_no_id(self):
        release = os_utils.OsRelease(
            os_release_file=self._write_os_release(
                textwrap.dedent(
                    """\
                NAME="Arch Linux"
                PRETTY_NAME="Arch Linux"
                ID_LIKE=archlinux
                VERSION_ID="foo"
                VERSION_CODENAME="bar"
            """
                )
            )
        )

        with pytest.raises(errors.OsReleaseIdError):
            release.id()

    def test_no_name(self):
        release = os_utils.OsRelease(
            os_release_file=self._write_os_release(
                textwrap.dedent(
                    """\
                ID=arch
                PRETTY_NAME="Arch Linux"
                ID_LIKE=archlinux
                VERSION_ID="foo"
                VERSION_CODENAME="bar"
            """
                )
            )
        )

        with pytest.raises(errors.OsReleaseNameError):
            release.name()

    def test_no_version_id(self):
        release = os_utils.OsRelease(
            os_release_file=self._write_os_release(
                textwrap.dedent(
                    """\
                NAME="Arch Linux"
                ID=arch
                PRETTY_NAME="Arch Linux"
                ID_LIKE=archlinux
                VERSION_CODENAME="bar"
            """
                )
            )
        )

        with pytest.raises(errors.OsReleaseVersionIdError):
            release.version_id()


class TestEnvironment:
    """Running on snap or container must be detected."""

    @pytest.mark.parametrize(
        ("snap_var", "app_name", "result"),
        [
            (None, "myapp", False),
            ("", "myapp", False),
            ("other", "myapp", False),
            ("myapp", "myapp", True),
        ],
    )
    def test_is_snap(self, mocker, snap_var, app_name, result):
        if snap_var is not None:
            mocker.patch.dict(os.environ, {"SNAP_NAME": snap_var}, clear=True)
        else:
            mocker.patch.dict(os.environ, {}, clear=True)

        assert os_utils.is_snap(app_name) == result

    def test_is_inside_container_has_dockerenv(self, mocker):
        mocker.patch("os.path.exists", new=lambda x: "/.dockerenv" in x)
        assert os_utils.is_inside_container()

    def test_is_inside_container_has_containerenv(self, mocker):
        mocker.patch("os.path.exists", new=lambda x: "/run/.containerenv" in x)
        assert os_utils.is_inside_container()

    def test_is_inside_container_no_files(self, mocker):
        mocker.patch("os.path.exists", return_value=False)
        assert os_utils.is_inside_container() is False


class TestMount:
    """Check mount and unmount calls."""

    def test_mount(self, mocker):
        mock_call = mocker.patch("subprocess.check_call")
        os_utils.mount("/dev/node", "/mountpoint", "some", "args")
        mock_call.assert_called_once_with(
            ["/bin/mount", "some", "args", "/dev/node", "/mountpoint"]
        )

    def test_mount_overlayfs(self, mocker):
        mock_call = mocker.patch("subprocess.check_call")
        os_utils.mount_overlayfs("/mountpoint", "some", "args")
        mock_call.assert_called_once_with(
            ["fuse-overlayfs", "some", "args", "/mountpoint"]
        )

    def test_umount(self, mocker):
        mock_call = mocker.patch("subprocess.check_call")
        os_utils.umount("/mountpoint", "some", "args")
        mock_call.assert_called_once_with(
            ["/bin/umount", "some", "args", "/mountpoint"]
        )

    def test_umount_retry(self, mocker):
        gen = itertools.count()

        def side_effect(*args):  # pylint: disable=unused-argument
            if next(gen) < 1:
                raise subprocess.CalledProcessError(cmd="cmd", returncode=42)

        mock_call = mocker.patch("subprocess.check_call", side_effect=side_effect)
        mock_sleep = mocker.patch("time.sleep")

        os_utils.umount("/mountpoint")
        assert mock_call.mock_calls == [
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
        ]
        assert mock_sleep.mock_calls == [call(1)]

    def test_umount_retry_fail(self, mocker):
        mock_call = mocker.patch(
            "subprocess.check_call",
            side_effect=subprocess.CalledProcessError(cmd="cmd", returncode=42),
        )
        mock_sleep = mocker.patch("time.sleep")
        with pytest.raises(subprocess.CalledProcessError) as raised:
            os_utils.umount("/mountpoint")
        assert str(raised.value) == "Command 'cmd' returned non-zero exit status 42."
        assert mock_call.mock_calls == [
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
            call(["/bin/umount", "/mountpoint"]),
        ]
        assert mock_sleep.mock_calls == [
            call(1),
            call(1),
            call(1),
            call(1),
            call(1),
        ]


@pytest.mark.parametrize(
    ("command", "log_calls"),
    [
        (["true"], []),
        (["echo", "hi"], [mock.call(":: hi")]),
        (
            ["bash", "-c", "echo Line 1; echo Line 2; echo Line 3 >> /dev/stderr"],
            [
                mock.call(":: Line 1"),
                mock.call(":: Line 2"),
                mock.call(":: Line 3"),
            ],
        ),
    ],
)
def test_process_run_output_correct(command: list[str], log_calls):
    mock_logger = mock.Mock()
    os_utils.process_run(command, mock_logger)

    assert mock_logger.mock_calls == log_calls
