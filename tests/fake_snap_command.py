# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2018-2021 Canonical Ltd.
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
import shutil
import subprocess

import craft_parts.packages.snaps

# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument


class FakeSnapCommand:
    """Mock the snap command."""

    def __init__(self, mocker):
        self.calls = []
        self.install_success = True
        self.refresh_success = True
        self.download_side_effect = None
        self.fake_download = None
        self._email = "-"

        original_run = craft_parts.packages.snaps.subprocess.run
        original_check_output = craft_parts.packages.snaps.subprocess.check_output

        def side_effect_run(cmd, *args, **kwargs):
            return side_effect(original_run, cmd, *args, **kwargs)

        def side_effect_check_output(cmd, *args, **kwargs):
            if self._is_snap_command(cmd):
                self.calls.append(cmd)
                return self._fake_snap_command(cmd, *args, **kwargs)

            return side_effect(original_check_output, cmd, *args, **kwargs)

        def side_effect(original, cmd, *args, **kwargs):
            if self._is_snap_command(cmd):
                self.calls.append(cmd)
                return self._fake_snap_command(cmd, *args, **kwargs)

            return original(cmd, *args, **kwargs)

        mocker.patch("craft_parts.packages.snaps.subprocess.run", side_effect_run)
        mocker.patch(
            "craft_parts.packages.snaps.subprocess.check_output",
            side_effect_check_output,
        )

    def login(self, email):
        self._email = email

    def _get_snap_cmd(self, cmd) -> tuple[str, list[str]]:
        try:
            snap_cmd_index = cmd.index("snap")
        except ValueError:
            return "", []

        try:
            return cmd[snap_cmd_index + 1], cmd[snap_cmd_index + 2 :]
        except IndexError:
            return "", []

    def _is_snap_command(self, cmd):
        snap_cmd, _ = self._get_snap_cmd(cmd)
        return snap_cmd in ["install", "refresh", "whoami", "download"]

    def _fake_snap_command(self, cmd, *args, **kwargs):
        cmd, params = self._get_snap_cmd(cmd)

        if cmd == "install" and not self.install_success:
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

        if cmd == "refresh" and not self.refresh_success:
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

        if cmd == "whoami":
            return f"email: {self._email}".encode()

        if (
            cmd == "download"
            and self.download_side_effect is not None
            and not self.download_side_effect.pop(0)
        ):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

        if cmd == "download":
            if self.fake_download:
                dest = os.path.join(kwargs["cwd"], params[0] + ".snap")
                shutil.copyfile(self.fake_download, dest)
            return b"Downloaded  "

        return None
