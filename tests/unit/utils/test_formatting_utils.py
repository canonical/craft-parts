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

import pytest

from craft_parts.utils import formatting_utils


@pytest.mark.parametrize(
    "items,result",
    [
        [[], ""],
        [["foo"], "'foo'"],
        [["foo", "bar"], "'bar' & 'foo'"],
        [[3, 2, 1], "1, 2, & 3"],
    ],
)
def test_humanize_list(items, result):
    hl = formatting_utils.humanize_list(iter(items), "&")
    assert hl == result


@pytest.mark.parametrize(
    "items,item_format,result",
    [
        [["foo"], "{!r}", "'foo'"],
        [[1], "{!r}", "1"],
        [[42], "{:2x}", "2a"],
    ],
)
def test_humanize_list_item_format(items, item_format, result):
    hl = formatting_utils.humanize_list(iter(items), "&", item_format)
    assert hl == result


def test_pluraize():
    assert formatting_utils.pluralize([], "a", "b") == "a"
    assert formatting_utils.pluralize([1], "a", "b") == "a"
    assert formatting_utils.pluralize([1, 2], "a", "b") == "b"
