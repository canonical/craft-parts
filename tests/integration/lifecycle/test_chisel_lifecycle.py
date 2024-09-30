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
import logging
import os
import textwrap
from pathlib import Path

import pytest
import yaml

import craft_parts
from craft_parts import Step
from craft_parts.packages import deb, errors
from craft_parts.utils import os_utils

IS_CI: bool = os.getenv("CI") == "true"

# These are the Ubuntu versions that Chisel currently supports.
SUPPORTED_UBUNTU_VERSIONS = {"20.04", "22.04", "22.10", "24.04"}


def _current_release_supported() -> bool:
    """Whether Chisel supports the current running OS release."""
    release = os_utils.OsRelease()
    return (
        release.id() == "ubuntu" and release.version_id() in SUPPORTED_UBUNTU_VERSIONS
    )


@pytest.mark.skipif(not IS_CI, reason="This test needs 'chisel' and only runs on CI.")
def test_chisel_lifecycle(new_dir):
    """Integrated test for Chisel support.

    Note that since this test needs the "chisel" binary, it currently only runs on CI.
    """
    _parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: nil
            stage-packages: [ca-certificates_data]
        """
    )

    parts = yaml.safe_load(_parts_yaml)

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_slice", cache_dir=new_dir, work_dir=new_dir
    )

    chisel_supported = _current_release_supported()

    actions = lf.plan(Step.PRIME)

    if chisel_supported:
        with lf.action_executor() as ctx:
            ctx.execute(actions)

        root = Path(new_dir)
        assert (root / "prime/etc/ssl/certs/ca-certificates.crt").is_file()
        assert (root / "prime/usr/share/ca-certificates").is_dir()
    else:
        with pytest.raises(errors.ChiselError):
            with lf.action_executor() as ctx:
                ctx.execute(actions)


@pytest.mark.skipif(
    not _current_release_supported(), reason="Test needs Chisel support"
)
def test_chisel_error(tmp_path, caplog):
    """Test that the error that is raised when Chisel fails contains the expected information."""
    caplog.set_level(logging.DEBUG)
    install_path = tmp_path / "install"
    with pytest.raises(errors.ChiselError) as exc:
        deb.Ubuntu.unpack_stage_packages(
            stage_packages_path=Path("unused"),
            install_path=install_path,
            stage_packages=["invalid-chisel_slice"],
        )

    err = exc.value

    # Check that the error's "brief" lists the slices.
    expected_brief = "Failed to cut requested chisel slices: invalid-chisel_slice"
    assert err.brief == expected_brief

    # Check that the "details" contain the actual error from Chisel.
    chisel_error = ':: error: slices of package "invalid-chisel" not found'
    assert err.details is not None
    assert err.details == chisel_error
