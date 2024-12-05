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

from pathlib import Path

import pytest
from craft_parts.utils import process


@pytest.fixture
def case_dir() -> Path:
    return Path(__file__).parent / "test_process"


def test_simple_script(case_dir, capfd) -> None:
    process.run(["/bin/bash", case_dir / "simple.sh"])
    assert capfd.readouterr().out == "foo\n"


def test_complex_script(case_dir, capfd) -> None:
    def _build_expected(raw: list[int]) -> str:
        sorted_output = sorted(raw)
        return "\n".join([str(n) for n in sorted_output]) + "\n"

    result = process.run(["/bin/bash", case_dir / "complex.sh"])

    out, err = capfd.readouterr()
    out_n = [int(s) for s in out.split()]
    err_n = [int(s) for s in err.split()]

    # From complex.sh
    expected_out_size = 100
    expected_err_size = 300
    assert len(out_n) == expected_out_size
    assert len(err_n) == expected_err_size

    comb_n = out_n + err_n
    expected = _build_expected(comb_n)
    assert expected == result.combined.decode("utf-8")

    expected = _build_expected(out_n)
    assert expected == result.stdout.decode("utf-8")

    expected = _build_expected(err_n)
    assert expected == result.stderr.decode("utf-8")


def test_fails_on_check(case_dir) -> None:
    with pytest.raises(process.ProcessError) as raises:
        process.run(["/bin/bash", case_dir / "fails.sh"], check=True)

    assert raises.value.result.returncode == 1
    assert raises.value.result.stderr == b"Error: Not enough cows.\n"


def test_devnull(capfd):
    result = process.run(["echo", "hello"], stdout=process.DEVNULL)

    assert capfd.readouterr().out == ""
    assert result.stdout == b""
