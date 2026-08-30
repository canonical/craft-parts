# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2024 Canonical Ltd.
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


import pathlib
from typing import Literal

import craft_parts
import pytest
from craft_parts import sources
from typing_extensions import override


class FakeSourceModel(sources.BaseSourceModel, frozen=True):
    pattern = "^fake:"
    source_type: Literal["fake"] = "fake"


class FakeSource(sources.SourceHandler):
    source_model = FakeSourceModel

    @override
    def pull(self) -> None:
        """Build a fake source."""
        (self.part_src_dir / "It's a fake!").write_text(self.source)


@pytest.mark.parametrize(
    "source_info",
    [
        {"source": "fake://youtube.com/watch?v=H6yQOs93Cgg"},
        {"source-type": "fake", "source": "https://youtube.com/watch?v=H6yQOs93Cgg"},
    ],
)
def test_register_and_pull_fake_source(source_info, new_dir):
    parts = {
        "parts": {
            "foo": {
                "plugin": "nil",
                **source_info,
            }
        }
    }
    fake_file = pathlib.Path("parts", "foo", "src", "It's a fake!")

    lcm = craft_parts.LifecycleManager(
        parts, application_name="test_fake_source", cache_dir=new_dir
    )

    sources.register(FakeSource)
    with lcm.action_executor() as ctx:
        ctx.execute(craft_parts.Action("foo", craft_parts.Step.PULL))

    assert fake_file.read_text() == source_info["source"]
