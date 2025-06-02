# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

from copy import deepcopy

import pydantic
import pytest
from craft_parts import errors
from craft_parts.filesystem_mounts import (
    FilesystemMount,
    FilesystemMountItem,
    validate_filesystem_mounts,
)


def test_filesystem_mount_item_marshal_unmarshal():
    data = {
        "mount": "/",
        "device": "(default)",
    }

    data_copy = deepcopy(data)

    spec = FilesystemMountItem.unmarshal(data)
    assert spec.marshal() == data_copy


def test_filesystem_mount_item_unmarshal_not_dict():
    with pytest.raises(TypeError) as raised:
        FilesystemMountItem.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
    assert str(raised.value) == "filesystem_mount item data is not a dictionary"


@pytest.mark.parametrize(
    ("data", "error_regex"),
    [
        (
            {
                "mount": "",
                "device": "(default)",
            },
            r"1 validation error for FilesystemMountItem\nmount\n\s+String should have at least 1 character",
        ),
        (
            {
                "mount": "/",
                "device": "",
            },
            r"1 validation error for FilesystemMountItem\ndevice\n\s+String should have at least 1 character",
        ),
    ],
)
def test_filesystem_mount_item_unmarshal_empty_entries(data, error_regex):
    with pytest.raises(
        pydantic.ValidationError,
        match=error_regex,
    ):
        FilesystemMountItem.unmarshal(data)


def test_filesystem_mount_marshal_unmarshal():
    data = [
        {
            "mount": "/",
            "device": "foo",
        },
        {
            "mount": "/bar",
            "device": "baz",
        },
    ]

    data_copy = deepcopy(data)
    spec = FilesystemMount.unmarshal(data)

    assert spec.marshal() == data_copy


def test_filesystem_mount_unmarshal_not_list():
    with pytest.raises(TypeError) as raised:
        FilesystemMount.unmarshal(False)  # type: ignore[reportGeneralTypeIssues] # noqa: FBT003
    assert str(raised.value) == "filesystem_mount data is not a list"


@pytest.mark.parametrize(
    ("data", "error_regex"),
    [
        (
            [],
            r"1 validation error for FilesystemMount\n\s+Value should have at least 1 item after validation, not 0",
        ),
        (
            [
                {
                    "mount": "/",
                    "device": "foo",
                },
                {
                    "mount": "/",
                    "device": "foo",
                },
            ],
            r"1 validation error for FilesystemMount\n\s+Value error, Duplicate values in list",
        ),
        (
            [
                {
                    "mount": "/foo",
                    "device": "foo",
                },
            ],
            r"1 validation error for FilesystemMount\n\s+Value error, The first entry in a filesystem must map the '/' mount.",
        ),
    ],
)
def test_filesystem_mount_unmarshal_invalid(data, error_regex):
    with pytest.raises(
        pydantic.ValidationError,
        match=error_regex,
    ):
        FilesystemMount.unmarshal(data)


@pytest.mark.parametrize("filesystem_mounts", [None])
def test_validate_filesystem_mounts_success_feature_disabled(filesystem_mounts):
    validate_filesystem_mounts(filesystem_mounts)


@pytest.mark.usefixtures("enable_all_features")
@pytest.mark.parametrize(
    ("filesystem_mounts", "brief", "details"),
    [
        (
            {"test": "test", "test2": "test"},
            "Exactly one filesystem must be defined.",
            None,
        ),
        (
            {"test": "test"},
            "'default' filesystem missing.",
            None,
        ),
        (
            {
                "default": [
                    {
                        "mount": "/a",
                        "device": "",
                    },
                    {
                        "mount": "/",
                        "device": "",
                    },
                ]
            },
            "Filesystem validation failed.",
            "- String should have at least 1 character in field 'device'",
        ),
        (
            {
                "default": [
                    {
                        "mount": "/a",
                        "device": "foo",
                    }
                ]
            },
            "Filesystem validation failed.",
            "- Value error, The first entry in a filesystem must map the '/' mount. in field ''",
        ),
    ],
)
def test_validate_filesystem_mounts_failure_feature_enabled(
    filesystem_mounts, brief, details
):
    with pytest.raises(errors.FilesystemMountError) as exc_info:
        validate_filesystem_mounts(filesystem_mounts)

    assert exc_info.value.brief == brief
    assert exc_info.value.details == details
