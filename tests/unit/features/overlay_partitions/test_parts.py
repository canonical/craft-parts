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

from pathlib import Path

import pytest
from craft_parts import parts
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

    def test_part_install_dirs(self, new_dir, partitions):
        p = Part("foo", {"organize": {"foo": "bar"}}, partitions=partitions)
        assert p.part_install_dirs == {
            "default": Path(new_dir / "parts/foo/install"),
            "mypart": Path(new_dir / "partitions/mypart/parts/foo/install"),
            "yourpart": Path(new_dir / "partitions/yourpart/parts/foo/install"),
        }

    def test_part_install_dirs_organize_to_overlay(self, new_dir, partitions):
        p = Part("foo", {"organize": {"foo": "(overlay)/bar"}}, partitions=partitions)
        assert p.part_install_dirs == {
            "default": Path(new_dir / "parts/foo/install"),
            "mypart": Path(new_dir / "partitions/mypart/parts/foo/install"),
            "yourpart": Path(new_dir / "partitions/yourpart/parts/foo/install"),
            "overlay": Path(new_dir / "overlay/overlay"),
        }

    def test_get_parts_with_overlay(self, partitions):
        p1 = Part("foo", {}, partitions=partitions)
        p2 = Part("bar", {"overlay-packages": ["pkg1"]}, partitions=partitions)
        p3 = Part("baz", {"overlay-script": "echo"}, partitions=partitions)
        p4 = Part("qux", {"overlay": ["*"]}, partitions=partitions)
        p5 = Part("quux", {"overlay": ["-etc/passwd"]}, partitions=partitions)
        p6 = Part("quuux", {"organize": {"f1": "(overlay)/f1"}}, partitions=partitions)

        p = parts.get_parts_with_overlay(part_list=[p1, p2, p3, p4, p5, p6])
        assert p == [p2, p3, p5, p6]
