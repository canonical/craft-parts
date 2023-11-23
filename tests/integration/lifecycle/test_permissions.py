# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
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

import os
import stat
import textwrap
from pathlib import Path

import craft_parts
import yaml
from craft_parts import Step


def test_part_permissions(new_dir, mock_chown):
    files = Path("files")
    files.mkdir()

    (files / "1.txt").touch()
    (files / "bar").mkdir()
    (files / "bar/2.txt").touch()

    parts_yaml = textwrap.dedent(
        """
        parts:
          my-part:
            plugin: dump
            source: files
            permissions:
              - path: 1.txt
                mode: "222"
              - path: bar/*
                owner: 1111
                group: 2222
        """
    )

    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_demo", cache_dir=new_dir
    )
    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert stat.S_IMODE(os.stat(Path("prime/1.txt")).st_mode) == 0o222
    chown_call = mock_chown[str(Path("prime/bar/2.txt").resolve())]
    assert chown_call.owner == 1111
    assert chown_call.group == 2222
