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


import pytest
from craft_parts import errors
from craft_parts.utils import layout_utils


@pytest.mark.parametrize("layouts", [None])
def test_validate_layouts_success_feature_disabled(layouts):
    layout_utils.validate_layouts(layouts)


@pytest.mark.usefixtures("enable_all_features")
@pytest.mark.parametrize(
    ("layouts", "message"),
    [
        (
            {"test": "test", "test2": "test"},
            "One and only one filesystem must be defined.",
        ),
        (
            {"test": "test"},
            "A 'default' filesystem must be defined.",
        ),
        (
            {"default": []},
            "The 'default' filesystem must defined at least one entry.",
        ),
        (
            {"default": [{"mount": "not_slash", "device": "(default)"}]},
            "The 'default' filesystem first entry must map the '/' mount.",
        ),
    ],
)
def test_validate_layouts_failure_feature_enabled(layouts, message):
    with pytest.raises(errors.FeatureError) as exc_info:
        layout_utils.validate_layouts(layouts)

    assert exc_info.value.brief == message
