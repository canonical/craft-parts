# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2024 Canonical Ltd.
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

import re
from typing import Literal

import pytest
from craft_parts.dirs import ProjectDirs
from craft_parts.parts import Part
from craft_parts.sources import LocalSource, base, errors, sources
from craft_parts.sources.tar_source import TarSource


class FakeSourceModel(base.BaseSourceModel, frozen=True):
    pattern = "a"  # Intentionally a very broad pattern, used below.
    source_type: Literal["fake"] = "fake"


class FakeSource(sources.SourceHandler):
    source_model = FakeSourceModel

    def pull(self) -> None:
        raise NotImplementedError


@pytest.fixture(autouse=True)
def reset_sources():
    sources._SOURCES.clear()


def test_register_source():
    assert "fake" not in sources._SOURCES

    sources.register(FakeSource)

    assert "fake" in sources._SOURCES


@pytest.mark.parametrize("source", sources._MANDATORY_SOURCES.values())
def test_register_builtin_source(source):
    with pytest.raises(
        ValueError, match="^Built-in source types cannot be overridden: '"
    ):
        sources.register(source)


def test_register_unregister_source():
    assert "fake" not in sources._SOURCES

    sources.register(FakeSource)

    assert "fake" in sources._SOURCES

    sources.unregister("fake")

    assert "fake" not in sources._SOURCES


@pytest.mark.parametrize(
    ("tc_url", "tc_handler"),
    [
        (".", LocalSource),
        (".tar.gz", TarSource),
        (".tar.bz2", TarSource),
        (".tgz", TarSource),
        (".tar", TarSource),
    ],
)
def test_get_source_handler_class(tc_url, tc_handler):
    h = sources._get_source_handler_class(tc_url)
    assert h == tc_handler


def test_get_source_handler_class_with_invalid_type():
    with pytest.raises(errors.InvalidSourceType) as raised:
        sources._get_source_handler_class(".", source_type="invalid")
    assert raised.value.source == "."


@pytest.mark.parametrize(
    ("source", "result"),
    [
        (".", "local"),
        (".7z", "7z"),
        (".deb", "deb"),
        (
            "http://archive.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.39-0ubuntu8.3_amd64.deb",
            "deb",
        ),
        (".rpm", "rpm"),
        (".snap", "snap"),
        (".tar.gz", "tar"),
        (".tar.bz2", "tar"),
        (".tar.zst", "tar"),
        (".tgz", "tar"),
        (".tar", "tar"),
        ("git:", "git"),
        ("git@", "git"),
        ("git+ssh:", "git"),
        ("git+https:", "git"),
        (".git", "git"),
        (".zip", "zip"),
    ],
)
def test_type_from_uri(source, result):
    assert sources.get_source_type_from_uri(source) == result


@pytest.mark.parametrize(
    "source",
    [
        # Sources that don't quite match the appropriate value.
        "7z",
        "bzr",
        "deb",
        "git",
        "lp",
        "rpm",
        "snap",
        "svn",
        "zip",
        "http://archive.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.39-0ubuntu8.3_amd64.deb?undetectable_source_type=True",
        # Sources that are wildly off
        "https://canonical.com",
    ],
)
def test_unknown_source_type_from_uri(source):
    with pytest.raises(errors.InvalidSourceType):
        sources.get_source_type_from_uri(source)


@pytest.mark.parametrize(
    ("source_type", "source_branch", "source_tag", "source_commit", "error"),
    [
        ("tar", "test_branch", None, None, "source-branch"),  # tar with source branch
        ("tar", None, "test_tag", None, "source-tag"),  # tar with source tag
        ("tar", None, None, "commit", "source-commit"),  # tar with source commit
    ],
)
def test_sources_with_branch_errors(
    new_dir, partitions, source_type, source_branch, source_tag, source_commit, error
):
    part_data = {
        "source": "https://source.com",
        "source-type": source_type,
    }

    if source_branch:
        part_data["source-branch"] = source_branch

    if source_tag:
        part_data["source-tag"] = source_tag

    if source_commit:
        part_data["source-commit"] = source_commit

    p1 = Part("p1", part_data)

    with pytest.raises(errors.InvalidSourceOption) as err:
        sources.get_source_handler(
            part=p1,
            project_dirs=ProjectDirs(partitions=partitions),
            cache_dir=new_dir,
        )
    assert err.value.source_type == source_type
    assert err.value.option == error


@pytest.mark.parametrize("uri", ["a", ".snappy", "some-tar", "a-deb", "git+a"])
def test_get_registered_source_type_from_uri_success(uri):
    sources.register(FakeSource)

    assert sources.get_source_type_from_uri(uri) == "fake"


@pytest.mark.parametrize("uri", [".snap", "some.tar", "a.deb", "git+https://a"])
def test_built_in_source_types_preferred_over_registered(uri: str):
    pattern = str(FakeSourceModel.pattern)
    assert re.search(pattern, uri), f"URI doesn't match FakeSource pattern: {uri!r}"
    sources.register(FakeSource)

    assert sources.get_source_type_from_uri(uri) != "fake"
