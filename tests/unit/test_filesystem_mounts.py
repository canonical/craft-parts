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
    FilesystemMounts,
    validate_filesystem_mounts,
)


def test_filesystem_mount_item_marshal_unmarshal():
    data = {
        "mount": "/",
        "device": "default",
    }

    data_copy = deepcopy(data)

    spec = FilesystemMountItem.unmarshal(data)
    assert spec.marshal() == data_copy


def test_filesystem_mount_item_unmarshal_not_dict():
    with pytest.raises(
        TypeError, match=r"^Filesystem input data must be a dictionary\.$"
    ):
        FilesystemMountItem.unmarshal(None)  # type: ignore[reportGeneralTypeIssues]


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


@pytest.mark.parametrize(
    "data",
    [
        [
            {
                "mount": "/",
                "device": "foo",
            },
            {
                "mount": "/bar",
                "device": "baz",
            },
        ],
        [
            {
                "mount": "/",
                "device": "foo",
            },
            {
                "mount": "/bar/a/b",
                "device": "baz",
            },
            {
                "mount": "/bar/a/c",
                "device": "bla",
            },
        ],
        [
            {
                "mount": "/",
                "device": "foo",
            },
            {
                "mount": "/a",
                "device": "bar",
            },
            {
                "mount": "/a/c",
                "device": "baz",
            },
            {
                "mount": "/b",
                "device": "qux",
            },
        ],
    ],
)
def test_filesystem_mount_marshal_unmarshal(data):
    data_copy = deepcopy(data)
    spec = FilesystemMount.unmarshal(data)

    assert spec.marshal() == data_copy


def test_filesystem_mount_unmarshal_not_list():
    with pytest.raises(TypeError, match=r"^Filesystem entry must be a list\.$"):
        FilesystemMount.unmarshal(None)  # type: ignore[reportGeneralTypeIssues]


@pytest.mark.parametrize(
    ("data", "error_regex"),
    [
        (
            False,
            r"Filesystem entry must be a list.",
        ),
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
                    "device": "bar",
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
        (
            [
                {
                    "mount": "/",
                    "device": "foo",
                },
                {
                    "mount": "/a/c",
                    "device": "baz",
                },
                {
                    "mount": "/foo",
                    "device": "bla",
                },
                {
                    "mount": "/b/c",
                    "device": "bla",
                },
                {
                    "mount": "/b",
                    "device": "baz",
                },
                {
                    "mount": "/a",
                    "device": "bar",
                },
            ],
            r"1 validation error for FilesystemMount\n\s+Value error, Entries in a filesystem must be ordered in increasing depth.\n- /a/c must be listed before /a\n- /b/c must be listed before /b",
        ),
        (
            [
                {
                    "mount": "/",
                    "device": "foo",
                },
                {
                    "mount": "/a/c",
                    "device": "baz",
                },
                {
                    "mount": "/a/b",
                    "device": "bla",
                },
                {
                    "mount": "/a",
                    "device": "bla",
                },
            ],
            r"1 validation error for FilesystemMount\n\s+Value error, Entries in a filesystem must be ordered in increasing depth.\n- /a/c must be listed before /a\n- /a/b must be listed before /a",
        ),
    ],
)
def test_filesystem_mount_unmarshal_invalid(data, error_regex):
    with pytest.raises(
        (pydantic.ValidationError, TypeError),
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
            "Only one filesystem can be defined.",
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
            {"default": False},
            "Filesystem validation failed.",
            "Filesystem entry must be a list.",
        ),
        (
            {"default": [False]},
            "Filesystem validation failed.",
            "Filesystem input data must be a dictionary.",
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
        (
            {
                "default": [
                    {
                        "mount": "/",
                        "device": "foo",
                    },
                    {
                        "mount": "/a/b",
                        "device": "bar",
                    },
                    {
                        "mount": "/a",
                        "device": "baz",
                    },
                ]
            },
            "Filesystem validation failed.",
            "- Value error, Entries in a filesystem must be ordered in increasing depth.\n- /a/b must be listed before /a in field ''",
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


def test_filesystem_mounts_marshal_unmarshal():
    data = {
        "default": [
            {
                "mount": "/",
                "device": "default",
            }
        ]
    }

    data_copy = deepcopy(data)

    spec = FilesystemMounts.unmarshal(data)
    assert spec.marshal() == data_copy


def test_filesystem_mounts_unmarshal_not_dict():
    with pytest.raises(TypeError, match="^filesystems is not a dictionary$"):
        FilesystemMounts.unmarshal(None)  # type: ignore[reportGeneralTypeIssues]


def test_filesystem_mounts_iterable():
    data = {
        "default": [
            {
                "mount": "/",
                "device": "default",
            }
        ]
    }

    filesystem_mounts = FilesystemMounts.unmarshal(data)
    for f in filesystem_mounts:
        print(f)


def test_filesystem_mounts_get():
    data = {
        "default": [
            {
                "mount": "/",
                "device": "foo",
            }
        ]
    }

    filesystem_mounts = FilesystemMounts.unmarshal(data)
    assert filesystem_mounts.get("default") == FilesystemMount(
        root=[FilesystemMountItem(mount="/", device="foo")]
    )
