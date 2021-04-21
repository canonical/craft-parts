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

from craft_parts.sources.cache import FileCache
from craft_parts.utils import file_utils


def test_file_cache(new_dir):
    digest = "algo/12345678"
    x = FileCache(name="test")

    # make sure file is not cached
    assert x.get(key=digest) is None

    test_file = Path("test_file")
    test_file.write_text("content")

    # cache it
    result = x.cache(filename="test_file", key=digest)
    assert result is not None

    cached_file = x.get(key=digest)
    assert result == cached_file

    cached_path = Path(result)
    assert cached_path == Path(
        new_dir, ".cache", "test", "craft-parts", "files", digest
    )

    # cache entry shouldn't be a hard link
    assert cached_path.stat().st_ino != test_file.stat().st_ino

    # but they must have the same contents
    test_hash = file_utils.calculate_hash("test_file", algorithm="sha1")
    cached_hash = file_utils.calculate_hash(result, algorithm="sha1")
    assert test_hash == cached_hash


@pytest.mark.usefixtures("new_dir")
def test_file_cache_clean():
    digest = "algo/12345678"
    x = FileCache(name="test")

    test_file = Path("test_file")
    test_file.write_text("content")

    result = x.cache(filename="test_file", key=digest)
    assert result is not None

    cached_path = Path(result)
    assert cached_path.is_file()

    x.clean()
    assert not cached_path.is_file()


@pytest.mark.usefixtures("new_dir")
def test_file_cache_nonfile():
    digest = "algo/12345678"
    x = FileCache(name="test")

    test_dir = Path("test_dir")
    test_dir.mkdir()

    result = x.cache(filename="test_dir", key=digest)
    assert result is None


@pytest.mark.usefixtures("new_dir")
def test_file_cache_non_existent():
    digest = "algo/12345678"
    x = FileCache(name="test")

    result = x.cache(filename="test_file", key=digest)
    assert result is None
