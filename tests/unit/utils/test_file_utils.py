# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

import pytest

from craft_parts.utils import file_utils


@pytest.fixture(autouse=True)
def setup_module_fixture(new_dir):
    pass


@pytest.mark.parametrize(
    "algo,digest",
    [
        ("md5", "9a0364b9e99bb480dd25e1f0284c8555"),
        ("sha1", "040f06fd774092478d450774f5ba30c5da78acc8"),
    ],
)
def test_calculate_hash(algo, digest):
    Path("test_file").write_text("content")
    assert file_utils.calculate_hash("test_file", algorithm=algo) == digest


def test_file_reader_iter():
    Path("test_file").write_text("content")
    gen = file_utils._file_reader_iter("test_file", block_size=4)
    assert [x for x in gen] == [b"cont", b"ent"]
