# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2026 Canonical Ltd.
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
import textwrap

import craft_parts
import pytest
import yaml
from craft_parts import Step


@pytest.mark.requires_root
def test_two_parts_organize_to_same_overlay(new_dir: pathlib.Path):
    parts_yaml = textwrap.dedent(
        """\
            parts:
              a:
                plugin: nil
                override-build: |
                  mkdir -p "${CRAFT_PART_INSTALL}/my-dir/subdir-a"
                organize:
                  '*': (overlay)/
              b:
                plugin: nil
                override-build: |
                  mkdir -p "${CRAFT_PART_INSTALL}/my-dir/subdir-b"
                  touch "${CRAFT_PART_INSTALL}/my-dir/subdir-b/my-file"
                organize:
                  '*': (overlay)/
              overlayer:
                plugin: nil
                overlay-script: |
                  echo 'Hi from overlay'
                  test -d "${CRAFT_OVERLAY}/my-dir/subdir-a"
                  test -d "${CRAFT_OVERLAY}/my-dir/subdir-b"
                  test -f "${CRAFT_OVERLAY}/my-dir/subdir-b/my-file"
        """
    )
    overlay_base = new_dir / "overlay_base"
    overlay_base.mkdir()

    parts = yaml.safe_load(parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts,
        application_name="test",
        cache_dir=new_dir,
        base_layer_dir=overlay_base,
        base_layer_hash=b"deadbeef",
        partitions=["default"],
    )
    actions = lf.plan(Step.PRIME)
    with lf.action_executor() as ctx:
        ctx.execute(actions)

    assert (lf.project_info.prime_dirs["default"] / "my-dir/subdir-b/my-file").is_file()
