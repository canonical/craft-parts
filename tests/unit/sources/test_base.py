# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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
from re import escape
from typing import Literal

import pytest
import requests
from craft_parts import ProjectDirs
from craft_parts.sources import cache, errors
from craft_parts.sources.base import (
    BaseFileSourceModel,
    BaseSourceModel,
    FileSourceHandler,
    SourceHandler,
)
from overrides import overrides

# pylint: disable=attribute-defined-outside-init


class FooSourceModel(BaseSourceModel, frozen=True):
    source_type: Literal["foo"] = "foo"


class FooSourceHandler(SourceHandler):
    """A source handler that does nothing."""

    source_model = FooSourceModel

    def pull(self) -> None:
        """Pull this source type."""


class TestSourceHandler:
    """Verify SourceHandler methods and attributes."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        self._dirs = ProjectDirs(partitions=partitions)
        self.source = FooSourceHandler(
            source="source",
            part_src_dir=Path("parts/foo/src"),
            cache_dir=new_dir,
            project_dirs=self._dirs,
        )

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
            "^Can't instantiate abstract class FaultySource with(out an implementation for)? "
            "abstract methods? '?pull'?$"
        )
        with pytest.raises(TypeError, match=expected):
            FaultySource(  # type: ignore[reportGeneralTypeIssues]
                source=".",
                part_src_dir=Path(),
                cache_dir=Path(),
                project_dirs=self._dirs,
            )


class BarFileSourceModel(BaseFileSourceModel, frozen=True):
    source_type: Literal["bar"] = "bar"


class BarFileSource(FileSourceHandler):
    """A file source handler."""

    source_model = BarFileSourceModel

    @overrides
    def provision(
        self,
        dst: Path,
        keep: bool = False,  # noqa: FBT001, FBT002
        src: Path | None = None,
    ) -> None:
        """Extract source payload."""
        self.provision_dst = dst
        self.provision_keep = keep
        self.provision_src = src


class TestFileSourceHandler:
    """Verify FileSourceHandler methods and attributes."""

    def set_source(self, cache_dir, **kwargs) -> None:
        """Set the source."""
        source_kwargs = {
            "source": "source",
            "part_src_dir": Path("parts/foo/src"),
            "project_dirs": self._dirs,
            "cache_dir": cache_dir,
        }
        source_kwargs.update(kwargs)
        self.source = BarFileSource(**source_kwargs)

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir, partitions):
        self._dirs = ProjectDirs(partitions=partitions)
        self.set_source(cache_dir=new_dir)

    def test_pull_file(self, new_dir):
        self.set_source(source="src/my_file", cache_dir=new_dir)
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
        self.set_source(
            cache_dir=new_dir,
            source="src/my_file",
            source_checksum="md5/9a0364b9e99bb480dd25e1f0284c8555",
        )
        Path("src").mkdir()
        Path("src/my_file").write_text("content")
        Path("parts/foo/src").mkdir(parents=True)

        self.source.pull()

        assert self.source.provision_dst == Path("parts/foo/src")
        assert self.source.provision_keep is False
        assert self.source.provision_src == Path("parts/foo/src/my_file")

        dest = Path(new_dir, "parts", "foo", "src", "my_file")
        assert dest.is_file()

    def test_pull_file_checksum_error(self, new_dir):
        self.set_source(
            cache_dir=new_dir, source="src/my_file", source_checksum="md5/12345"
        )
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
        self.set_source(
            cache_dir=new_dir,
            source="http://test.com/some_file",
            source_checksum="md5/9a0364b9e99bb480dd25e1f0284c8555",
        )
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
        self.set_source(
            cache_dir=new_dir,
            source="http://test.com/some_file",
            source_checksum="md5/9a0364b9e99bb480dd25e1f0284c8555",
        )
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

    def test_pull_url_not_found(self, requests_mock, new_dir):
        self.set_source(cache_dir=new_dir, source="http://test.com/some_file")
        requests_mock.get(
            self.source.source,
            status_code=requests.codes.not_found,
            reason="Not found",
        )

        expected = (
            f"Failed to pull source: '{self.source.source}' not found.\n"
            "Make sure the source path is correct and accessible."
        )
        with pytest.raises(errors.SourceNotFound, match=expected):
            self.source.pull()

    @pytest.mark.parametrize(
        "error_code",
        [requests.codes.unauthorized, requests.codes.internal_server_error],
    )
    def test_pull_url_http_error(self, requests_mock, new_dir, error_code):
        self.set_source(cache_dir=new_dir, source="http://test.com/some_file")
        requests_mock.get(self.source.source, status_code=error_code, reason="Error")

        expected = escape(
            f"Cannot process request (Error: {error_code}): {self.source.source}\n"
            "Check your URL and permissions and try again."
        )
        with pytest.raises(errors.HttpRequestError, match=expected):
            self.source.pull()

    def test_file_source_abstract_methods(self):
        class FaultyFileSource(FileSourceHandler):
            """A file source handler that doesn't implement abstract methods."""

        expected = (
            r"^Can't instantiate abstract class FaultyFileSource with(out an "
            r"implementation for)? abstract methods? '?provision'?$"
        )
        with pytest.raises(TypeError, match=expected):
            FaultyFileSource(  # type: ignore[reportGeneralTypeIssues]
                source=None,  # type: ignore[reportGeneralTypeIssues]
                part_src_dir=None,  # type: ignore[reportGeneralTypeIssues]
                cache_dir=Path(),
                project_dirs=self._dirs,
            )
