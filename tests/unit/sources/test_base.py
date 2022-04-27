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

from pathlib import Path
from typing import Optional

import pytest
from overrides import overrides

from craft_parts.sources import cache, errors
from craft_parts.sources.base import FileSourceHandler, SourceHandler

# pylint: disable=attribute-defined-outside-init


class FooSourceHandler(SourceHandler):
    """A source handler that does nothing."""

    def pull(self) -> None:
        """Pull this source type."""


class TestSourceHandler:
    """Verify SourceHandler methods and attributes."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        self.source = FooSourceHandler(
            source="source",
            part_src_dir=Path("parts/foo/src"),
            cache_dir=new_dir,
        )

    def test_source(self):
        assert self.source.source_tag is None
        assert self.source.source_commit is None
        assert self.source.source_branch is None
        assert self.source.source_depth is None
        assert self.source.source_checksum is None
        assert self.source.source_submodules is None
        assert self.source.command is None

    def test_source_check_if_outdated(self):
        with pytest.raises(errors.SourceUpdateUnsupported) as raised:
            self.source.check_if_outdated("/some/file")
        assert raised.value.name == "FooSourceHandler"

    def test_source_update(self):
        with pytest.raises(errors.SourceUpdateUnsupported) as raised:
            self.source.update()
        assert raised.value.name == "FooSourceHandler"

    def test_source_abstract_methods(self):
        class FaultySource(SourceHandler):
            """A source handler that doesn't implement abstract methods."""

        expected = (
            "^Can't instantiate abstract class FaultySource with "
            "abstract methods? pull$"
        )
        with pytest.raises(TypeError, match=expected):
            # pylint: disable=abstract-class-instantiated
            FaultySource(  # type: ignore
                source=".", part_src_dir=Path(), cache_dir=Path()
            )


class BarFileSource(FileSourceHandler):
    """A file source handler."""

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,
        src: Optional[Path] = None,
    ) -> None:
        """Extract source payload."""
        self.provision_dst = dst
        self.provision_keep = keep
        self.provision_src = src


class TestFileSourceHandler:
    """Verify FileSourceHandler methods and attributes."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        self.source = BarFileSource(
            source="source",
            part_src_dir=Path("parts/foo/src"),
            cache_dir=new_dir,
        )

    def test_file_source(self):
        assert self.source.source_tag is None
        assert self.source.source_commit is None
        assert self.source.source_branch is None
        assert self.source.source_depth is None
        assert self.source.source_checksum is None
        assert self.source.source_submodules is None
        assert self.source.command is None

    def test_pull_file(self, new_dir):
        self.source.source = "src/my_file"
        Path("src").mkdir()
        Path("src/my_file").write_text("content")
        Path("parts/foo/src").mkdir(parents=True)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/my_file")

        dest = Path(new_dir, "parts", "foo", "src", "my_file")
        assert dest.is_file()

    def test_pull_file_error(self):
        self.source.source = "src/my_file"

        with pytest.raises(errors.SourceNotFound) as raised:
            self.source.pull()
        assert raised.value.source == "src/my_file"

    def test_pull_file_checksum(self, new_dir):
        self.source.source = "src/my_file"
        self.source.source_checksum = "md5/9a0364b9e99bb480dd25e1f0284c8555"
        Path("src").mkdir()
        Path("src/my_file").write_text("content")
        Path("parts/foo/src").mkdir(parents=True)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/my_file")

        dest = Path(new_dir, "parts", "foo", "src", "my_file")
        assert dest.is_file()

    @pytest.mark.usefixtures("new_dir")
    def test_pull_file_checksum_error(self):
        self.source.source = "src/my_file"
        self.source.source_checksum = "md5/12345"
        Path("src").mkdir()
        Path("src/my_file").write_text("content")
        Path("parts/foo/src").mkdir(parents=True)

        with pytest.raises(errors.ChecksumMismatch) as raised:
            self.source.pull()
        assert raised.value.expected == "12345"
        assert raised.value.obtained == "9a0364b9e99bb480dd25e1f0284c8555"

    def test_pull_url(self, requests_mock, new_dir):
        self.source.source = "http://test.com/some_file"
        requests_mock.get(self.source.source, text="content")
        Path("parts/foo/src").mkdir(parents=True)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/some_file")

        downloaded = Path(new_dir, "parts", "foo", "src", "some_file")
        assert downloaded.is_file()

    def test_pull_url_checksum(self, requests_mock, new_dir):
        self.source.source = "http://test.com/some_file"
        self.source.source_checksum = "md5/9a0364b9e99bb480dd25e1f0284c8555"
        requests_mock.get(self.source.source, text="content")
        Path("parts/foo/src").mkdir(parents=True)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/some_file")

        downloaded = Path(new_dir, "parts", "foo", "src", "some_file")
        assert downloaded.is_file()

        file_cache = cache.FileCache(new_dir)
        cached = file_cache.get(key=self.source.source_checksum)
        assert cached is not None
        assert Path(cached).read_bytes() == b"content"

    def test_pull_url_checksum_cached(self, requests_mock, new_dir):
        self.source.source = "http://test.com/some_file"
        self.source.source_checksum = "md5/9a0364b9e99bb480dd25e1f0284c8555"
        Path("parts/foo/src").mkdir(parents=True)
        requests_mock.get(self.source.source, text="other_content")

        # pre-cache this file
        Path("my_file").write_text("content")
        file_cache = cache.FileCache(new_dir)
        file_cache.cache(filename="my_file", key=self.source.source_checksum)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/some_file")

        downloaded = Path(new_dir, "parts", "foo", "src", "some_file")
        assert downloaded.is_file()
        assert downloaded.read_bytes() == b"content"

    def test_file_source_abstract_methods(self):
        class FaultyFileSource(FileSourceHandler):
            """A file source handler that doesn't implement abstract methods."""

        expected = (
            "^Can't instantiate abstract class FaultyFileSource with "
            "abstract methods? provision$"
        )
        with pytest.raises(TypeError, match=expected):
            # pylint: disable=abstract-class-instantiated
            FaultyFileSource(
                source=None, part_src_dir=None, cache_dir=Path()  # type: ignore
            )
