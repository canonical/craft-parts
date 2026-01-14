# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2025 Canonical Ltd.
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

from tests.unit.executor.test_organize import organize_and_assert


@pytest.mark.parametrize(
    "data",
    [
        # simple_file
        {
            "setup_files": [Path("foo")],
            "organize_map": {Path("foo"): "bar"},
            "expected": [(["bar"], "")],
        },
        # simple_dir_with_file
        {
            "setup_dirs": ["foodir"],
            "setup_files": [Path("foodir", "foo")],
            "organize_map": {Path("foodir"): "bardir"},
            "expected": [(["bardir"], ""), (["foo"], "bardir")],
        },
        # organize into overlay
        {
            "setup_files": [Path("foo")],
            "organize_map": {Path("foo"): "(overlay)/bar"},
            "expected": [([], ""), (["bar"], "../overlay_dir")],
        },
    ],
)
def test_organize(new_dir, data):
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=False,
        install_dirs={
            "default": Path(new_dir / "install"),
            "overlay": Path(new_dir / "overlay_dir"),
        },
    )

    # Verify that it can be organized again by overwriting
    organize_and_assert(
        tmp_path=new_dir,
        setup_dirs=data.get("setup_dirs", []),
        setup_files=data.get("setup_files", []),
        setup_symlinks=data.get("setup_symlinks", []),
        organize_map=data["organize_map"],
        expected=data["expected"],
        expected_message=data.get("expected_message"),
        expected_overwrite=data.get("expected_overwrite"),
        overwrite=True,
        install_dirs={
            "default": Path(new_dir / "install"),
            "overlay": Path(new_dir / "overlay_dir"),
        },
    )
