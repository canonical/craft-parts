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

from collections.abc import Iterable
from pathlib import Path

import pytest
from craft_parts.utils import fork_utils


@pytest.fixture
def case_dir() -> Path:
    return Path(__file__).parent / "test_fork_utils"


def test_simple_script(case_dir, capfd) -> None:
    fork_utils.run(["/bin/bash", case_dir / "simple.sh"])
    assert capfd.readouterr().out == "foo\n"


def test_complex_script(case_dir, capfd) -> None:
    def build_string_from_iter(it: Iterable[int]) -> str:
        return "\n".join({str(n) for n in it}) + "\n"

    result = fork_utils.run(["/bin/bash", case_dir / "complex.sh"])
    assert build_string_from_iter(range(0, 400)) == result.combined.decode("utf-8")

    assert build_string_from_iter(range(0, 400, 4)) == capfd.readouterr().out


def test_fails_on_check(case_dir) -> None:
    with pytest.raises(fork_utils.ForkError) as raises:
        fork_utils.run(["/bin/bash", case_dir / "fails.sh"], check=True)

    assert raises.value.result.returncode == 1
