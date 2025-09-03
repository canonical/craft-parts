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
from craft_parts.parts import Part


class TestPartData:
    """Test basic part creation and representation."""

    @pytest.mark.parametrize(
        ("organize", "result"),
        [
            ({}, False),
            ({"this": "that"}, False),
            ({"foo": "(default)/bar"}, False),
            ({"foo": "(overlay)/bar"}, True),
            ({"this": "that", "foo": "(overlay)/bar"}, True),
        ],
    )
    def test_part_organizes_to_overlay(self, partitions, organize, result):
        p = Part("foo", {"organize": organize}, partitions=partitions)
        assert p.organizes_to_overlay == result
