# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Unit tests for the lifecycle manager."""

import textwrap

import pytest
import yaml

from craft_parts import errors, manager


class TestLifecycleManager:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, new_dir):
        # pylint: disable=attribute-defined-outside-init
        self._dir = new_dir
        yaml_data = textwrap.dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )
        self._data = yaml.safe_load(yaml_data)
        # pylint: enable=attribute-defined-outside-init

    def test_invalid_arch(self):
        with pytest.raises(errors.InvalidArchitecture) as raised:
            manager.LifecycleManager(
                self._data, application_name="test_manager", arch="invalid"
            )
        assert raised.value.arch_name == "invalid"

    def test_project_info(self):
        lf = manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            work_dir="work_dir",
            arch="aarch64",
            parallel_build_count=16,
            custom="foo",
        )
        info = lf.project_info

        assert info.application_name == "test_manager"
        assert info.target_arch == "arm64"
        assert info.arch_triplet == "aarch64-linux-gnu"
        assert info.plugin_version == "v2"
        assert info.parallel_build_count == 16
        assert info.dirs.parts_dir == self._dir / "work_dir" / "parts"
        assert info.dirs.stage_dir == self._dir / "work_dir" / "stage"
        assert info.dirs.prime_dir == self._dir / "work_dir" / "prime"
        assert info.custom_args == ["custom"]
        assert info.custom == "foo"
