# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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
from craft_parts import callbacks, overlays
from craft_parts.executor import ExecutionContext, Executor
from craft_parts.infos import ProjectInfo
from craft_parts.parts import Part

from tests.unit.executor import test_executor


@pytest.mark.usefixtures("new_dir")
class TestExecutor(test_executor.TestExecutor):
    """Verify executor class methods with overlays."""


class TestPackages(test_executor.TestPackages):
    """Verify package installation during the execution phase with overlays."""


class TestExecutionContext(test_executor.TestExecutionContext):
    """Verify execution context methods with overlays."""


class TestExecutionContextOverlays:
    """Verify execution context methods specifically for overlays."""

    def setup_method(self):
        callbacks.unregister_all()

    def teardown_class(self):
        callbacks.unregister_all()

    def test_prologue_overlay_packages(self, new_dir, mocker):
        """Check that the overlay package cache is not touched if the part doesn't have overlay packages"""
        mock_mount = mocker.patch.object(overlays, "PackageCacheMount")

        p1 = Part("p1", {"plugin": "nil", "overlay-script": "echo overlay"})
        info = ProjectInfo(application_name="test", cache_dir=new_dir, custom="custom")
        e = Executor(project_info=info, part_list=[p1])

        with ExecutionContext(executor=e):
            assert not mock_mount.called

    def test_configure_overlay(self, new_dir, mocker, partitions):
        """Check that the configure_overlay callback is called when mounting the overlay's package cache."""

        mocker.patch.object(overlays.OverlayManager, "mount_pkg_cache")
        mocker.patch.object(overlays.OverlayManager, "unmount")

        # This list will contain a record of the calls that are made, in order.
        call_order = []

        def configure_overlay(overlay_dir: Path, project_info: ProjectInfo) -> None:
            call_order.append(f"configure_overlay: {overlay_dir} {project_info.custom}")

        def refresh_packages_list() -> None:
            call_order.append("refresh_packages_list")

        callbacks.register_configure_overlay(configure_overlay)
        mocker.patch.object(
            overlays.PackageCacheMount,
            "refresh_packages_list",
            side_effect=refresh_packages_list,
        )

        p1 = Part("p1", {"plugin": "nil", "overlay-packages": ["fake-pkg"]})
        info = ProjectInfo(application_name="test", cache_dir=new_dir, custom="custom")
        e = Executor(project_info=info, part_list=[p1])

        with ExecutionContext(executor=e):
            # The `configure_overlay()` callback must've been called _before_
            # refresh_packages_list().
            assert call_order == [
                f"configure_overlay: {info.overlay_mount_dir} custom",
                "refresh_packages_list",
            ]
