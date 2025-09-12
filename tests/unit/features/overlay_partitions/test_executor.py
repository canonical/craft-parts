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
from craft_parts.executor import Executor
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part


@pytest.mark.usefixtures("new_dir")
class TestExecutor:
    """Verify executor class methods with partitions and overlays."""

    @pytest.mark.parametrize(
        ("parts", "level"),
        [
            ([], 0),
            ([Part("p1", {"plugin": "nil"})], 0),
            ([Part("p1", {"plugin": "nil"}), Part("p2", {"plugin": "nil"})], 0),
            (
                [
                    Part("p1", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                    Part("p2", {"plugin": "nil"}),
                ],
                1,
            ),
            (
                [
                    Part("p1", {"plugin": "nil"}),
                    Part("p2", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                ],
                1,
            ),
            (
                [
                    Part("p1", {"plugin": "nil"}),
                    Part("p2", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                    Part("p3", {"plugin": "nil"}),
                    Part("p4", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                ],
                2,
            ),
            (
                [
                    Part("p1", {"plugin": "nil"}),
                    Part("p2", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                    Part("p3", {"plugin": "nil"}),
                    Part("p4", {"plugin": "nil"}),
                    Part("p5", {"plugin": "nil"}),
                    Part("p6", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                ],
                2,
            ),
            (
                [
                    Part("p1", {"plugin": "nil"}),
                    Part("p2", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                    Part("p3", {"plugin": "nil", "organize": {"foo": "(overlay)/bar"}}),
                    Part("p4", {"plugin": "nil"}),
                ],
                2,
            ),
        ],
    )
    def test_cache_level(self, new_dir, partitions, parts, level):
        info = ProjectInfo(
            application_name="test", cache_dir=new_dir, partitions=partitions
        )
        e = Executor(project_info=info, part_list=parts)
        assert e._overlay_manager.cache_level == level
