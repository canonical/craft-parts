# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
from craft_parts.executor import environment


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        # no replacement
        ("snapcraft_stage/usr/bin", "snapcraft_stage/usr/bin"),
        # replaced start
        (
            "$CRAFT_STAGE/usr/bin",
            "craft_stage/usr/bin",
        ),
        # replaced between
        (
            "--with-swig $CRAFT_STAGE/usr/swig",
            "--with-swig craft_stage/usr/swig",
        ),
        # project replacement
        (
            "$CRAFT_PROJECT_NAME-$CRAFT_PROJECT_VERSION",
            "project_name-version",
        ),
        # multiple replacement
        (
            "$CRAFT_PROJECT_NAME-$CRAFT_PROJECT_NAME",
            "project_name-project_name",
        ),
    ],
)
def test_string_replacements(subject, expected):
    result = environment._replace_attr(
        subject,
        {
            "$CRAFT_PROJECT_NAME": "project_name",
            "$CRAFT_PROJECT_VERSION": "version",
            "$CRAFT_STAGE": "craft_stage",
        },
    )
    assert result == expected


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        # no replacement
        (
            ["snapcraft_stage/usr/bin", "/usr/bin"],
            ["snapcraft_stage/usr/bin", "/usr/bin"],
        ),
        # replaced start
        (
            ["$CRAFT_STAGE/usr/bin", "/usr/bin"],
            ["craft_stage/usr/bin", "/usr/bin"],
        ),
        # replaced between
        (
            ["--without-python", "--with-swig $CRAFT_STAGE/usr/swig"],
            ["--without-python", "--with-swig craft_stage/usr/swig"],
        ),
    ],
)
def test_lists_with_string_replacements(subject, expected):
    result = environment._replace_attr(
        subject,
        {
            "$CRAFT_PROJECT_NAME": "project_name",
            "$CRAFT_PROJECT_VERSION": "version",
            "$CRAFT_STAGE": "craft_stage",
        },
    )
    assert result == expected


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        # no replacement
        (
            ("snapcraft_stage/usr/bin", "/usr/bin"),
            ["snapcraft_stage/usr/bin", "/usr/bin"],
        ),
        # replaced start
        (
            ("$CRAFT_STAGE/usr/bin", "/usr/bin"),
            ["craft_stage/usr/bin", "/usr/bin"],
        ),
        # replaced between
        (
            ("--without-python", "--with-swig $CRAFT_STAGE/usr/swig"),
            ["--without-python", "--with-swig craft_stage/usr/swig"],
        ),
    ],
)
def test_tuples_with_string_replacements(subject, expected):
    result = environment._replace_attr(
        subject,
        {
            "$CRAFT_PROJECT_NAME": "project_name",
            "$CRAFT_PROJECT_VERSION": "version",
            "$CRAFT_STAGE": "craft_stage",
        },
    )
    assert result == expected


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        # no replacement
        (
            {"1": "snapcraft_stage/usr/bin", "2": "/usr/bin"},
            {"1": "snapcraft_stage/usr/bin", "2": "/usr/bin"},
        ),
        # replaced start
        (
            {"1": "$CRAFT_STAGE/usr/bin", "2": "/usr/bin"},
            {"1": "craft_stage/usr/bin", "2": "/usr/bin"},
        ),
        # replaced between
        (
            {"1": "--without-python", "2": "--with-swig $CRAFT_STAGE/usr/swig"},
            {
                "1": "--without-python",
                "2": "--with-swig craft_stage/usr/swig",
            },
        ),
        # replace keys as well
        (
            {"$CRAFT_STAGE": "--with-swig $CRAFT_STAGE"},
            {"craft_stage": "--with-swig craft_stage"},
        ),
    ],
)
def test_dict_with_string_replacements(subject, expected):
    result = environment._replace_attr(
        subject,
        {
            "$CRAFT_PROJECT_NAME": "project_name",
            "$CRAFT_PROJECT_VERSION": "version",
            "$CRAFT_STAGE": "craft_stage",
        },
    )
    assert result == expected


def test_string_replacement_with_complex_data():
    subject = {
        "filesets": {
            "files": [
                "somefile",
                "$CRAFT_STAGE/file1",
                "CRAFT_STAGE/really",
            ]
        },
        "configflags": ["--with-python", "--with-swig $CRAFT_STAGE/swig"],
    }

    expected = {
        "filesets": {
            "files": [
                "somefile",
                "craft_stage/file1",
                "CRAFT_STAGE/really",
            ]
        },
        "configflags": [
            "--with-python",
            "--with-swig craft_stage/swig",
        ],
    }

    result = environment._replace_attr(
        subject,
        {
            "$CRAFT_PROJECT_NAME": "project_name",
            "$CRAFT_PROJECT_VERSION": "version",
            "$CRAFT_STAGE": "craft_stage",
        },
    )

    assert result == expected
