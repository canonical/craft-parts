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

import pytest
from craft_parts.utils import fork_utils


def test_no_raw_fd():
    with pytest.raises(ValueError, match="Raw file descriptors are not supported."):
        fork_utils.run(["true"], stdout=-999)


def test_devnull(capfd):
    result = fork_utils.run(["echo", "hello"], stdout=fork_utils.DEVNULL)

    assert capfd.readouterr().out == ""
    assert result.stdout == b"hello\n"
