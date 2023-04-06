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

import pytest

from craft_parts.dirs import ProjectDirs
from craft_parts.parts import Part
from craft_parts.sources import LocalSource, errors, sources
from craft_parts.sources.tar_source import TarSource


@pytest.mark.parametrize(
    "tc_url,tc_handler",
    [
        (".", LocalSource),
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
    "source,result",
    [
        (".tar.gz", "tar"),
        (".tar.bz2", "tar"),
        (".tgz", "tar"),
        (".tar", "tar"),
        ("git:", "git"),
        ("git@", "git"),
        ("git+ssh:", "git"),
        (".git", "git"),
        ("lp:", "bzr"),
        ("bzr:", "bzr"),
        ("svn:", "subversion"),
    ],
)
def test_type_from_uri(source, result):
    assert sources.get_source_type_from_uri(source) == result


@pytest.mark.parametrize(
    "source_type,source_branch,source_tag,source_commit,error",
    [
        ("tar", "test_branch", None, None, "source-branch"),  # tar with source branch
        ("tar", None, "test_tag", None, "source-tag"),  # tar with source tag
        ("tar", None, None, "commit", "source-commit"),  # tar with source commit
    ],
)
def test_sources_with_branch_errors(
    new_dir, source_type, source_branch, source_tag, source_commit, error
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
            part=p1, project_dirs=ProjectDirs(), cache_dir=new_dir
        )
    assert err.value.source_type == source_type
    assert err.value.option == error
