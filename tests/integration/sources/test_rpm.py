# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
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
import platform
import shutil
import subprocess
import textwrap
from pathlib import Path

import craft_parts
import pytest
import yaml
from craft_parts.actions import Action
from craft_parts.steps import Step


@pytest.fixture
def sample_rpm(tmp_path: Path) -> Path:
    """
    Create a basic .rpm file and return its path.
    """
    rpm_dir = tmp_path / "sample"
    rpm_dir.mkdir()

    # Add spec structure
    spec_dir = rpm_dir / "SPECS"
    spec_dir.mkdir()
    spec_file = spec_dir / "sample.spec"
    spec_file.write_text(
        textwrap.dedent(
            """
            Name: sample
            Version: 1.0
            Release: 0
            Summary: A sample package
            License: GPL

            %description
            A little sample package!

            %install
            mkdir -p %{buildroot}/etc
            bash -c "echo Sample contents > %{buildroot}/etc/sample.txt"

            %files
            /etc/sample.txt
            """
        )
    )

    # Define paths wo we don't litter the system with RPM stuff for this.
    rpmbuild_params = [
        f"--define=_topdir {rpm_dir}/build",
        f"--define=_dbpath {rpm_dir}/rpmdb",
        f"--define=_var {tmp_path}/var",
        f"--define=_tmppath {tmp_path}/tmp",
    ]

    subprocess.run(
        ["rpmbuild", "-bb", "--verbose", *rpmbuild_params, str(spec_file)],
        check=True,
        text=True,
        capture_output=True,
    )

    arch = platform.machine()
    rpm_path = rpm_dir / "build/RPMS" / arch / f"sample-1.0-0.{arch}.rpm"
    if not rpm_path.exists():
        raise FileNotFoundError("rpmbuild did not create the correct file.")
    return rpm_path


@pytest.mark.skipif(not shutil.which("rpmbuild"), reason="rpmbuild is not installed")
def test_source_rpm(sample_rpm, tmp_path):
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: nil
            source: {sample_rpm}
        """
    )

    result_dir = tmp_path / "result"
    result_dir.mkdir()

    parts = yaml.safe_load(parts_yaml)
    lf = craft_parts.LifecycleManager(
        parts, application_name="test_rpm", cache_dir=tmp_path, work_dir=result_dir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))

    expected_file = result_dir / "parts/foo/src/etc/sample.txt"
    assert expected_file.read_text() == "Sample contents\n"
