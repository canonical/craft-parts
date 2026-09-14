# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
"""Tests for package-related executor functionality."""

import pytest
from craft_parts import Part, ProjectInfo
from craft_parts.executor import Executor


@pytest.mark.slow
@pytest.mark.usefixtures("enable_build_slices")
def test_cut_build_slices(new_homedir_path, partitions):
    """Test that cutting slices works as expected."""

    first_part = Part(
        "foo",
        {"plugin": "nil", "build-slices": ["bash_bins", "base-files_bin"]},
        partitions=partitions,
    )

    info = ProjectInfo(
        application_name="test", cache_dir=new_homedir_path, partitions=partitions
    )
    slices_dir = info.dirs.build_slices_dir
    assert not slices_dir.exists()

    # Cut bash_bins and check the files
    e = Executor(project_info=info, part_list=[first_part])
    e.prologue()

    # Note: the addition of "base-files_bin" guarantees the usrmerged structure, so
    # these expected paths should work regardless of Ubuntu base (usrmerge behavior
    # changed in 24.04).
    assert slices_dir.exists()
    bash = slices_dir / "bin/bash"
    assert bash.is_file()

    # Cut a different set of build-slices and check that bash is no longer there
    second_part = Part(
        "foo",
        {"plugin": "nil", "build-slices": ["curl_bins", "base-files_bin"]},
        partitions=partitions,
    )
    e = Executor(project_info=info, part_list=[second_part])
    e.prologue()

    assert not bash.is_file()
    curl = slices_dir / "usr/bin/curl"
    assert curl.is_file()
