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


import subprocess
import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts.actions import Action
from craft_parts.steps import Step


@pytest.fixture
def sample_deb(tmp_path: Path) -> Path:
    """
    Create a basic .deb file and return its path.
    """
    deb_dir = tmp_path / "sample"
    deb_dir.mkdir()

    # Add control structure
    control_dir = deb_dir / "DEBIAN"
    control_dir.mkdir()
    control_file = control_dir / "control"
    control_file.write_text(
        textwrap.dedent(
            """
            Package: sample
            Version: 1.0.0
            Maintainer: Your Name <you@example.com>
            Description: Sample package
            Homepage: www.example.com
            Architecture: all
            """
        )
    )

    # Add the single text file to the package
    etc = deb_dir / "etc"
    etc.mkdir()
    sample_file = etc / "sample.txt"
    sample_file.write_text("Sample contents")

    target_deb = tmp_path / "sample.deb"

    subprocess.check_call(["dpkg", "-b", str(deb_dir), str(target_deb)])

    return target_deb


def test_source_deb(sample_deb, tmp_path):
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: nil
            source: {sample_deb}
        """
    )

    result_dir = tmp_path / "result"
    result_dir.mkdir()

    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_deb", cache_dir=tmp_path, work_dir=result_dir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    expected_file = result_dir / "parts/foo/src/etc/sample.txt"
    assert expected_file.read_text() == "Sample contents"
