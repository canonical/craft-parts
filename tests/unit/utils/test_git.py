# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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

import pytest
from craft_parts.utils.git import get_git_command


@pytest.mark.parametrize(
    ("which_result", "expected_command"),
    [
        (None, "git"),
        ("/usr/bin/craft.git", "/usr/bin/craft.git"),
        (
            "/snap/snapcraft/current/libexec/snapcraft/craft.git",
            "/snap/snapcraft/current/libexec/snapcraft/craft.git",
        ),
    ],
)
def test_get_git_command(which_result, expected_command, mocker):
    mocker.patch.object(shutil, "which", return_value=which_result)
    get_git_command.cache_clear()

    git_command = get_git_command()
    assert git_command == expected_command
