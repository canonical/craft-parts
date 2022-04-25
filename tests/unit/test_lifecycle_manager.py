# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Unit tests for the lifecycle manager."""

import sys
import textwrap
from typing import Any, Dict
from unittest.mock import ANY, call

import pytest
import yaml

from craft_parts import errors
from craft_parts.lifecycle_manager import LifecycleManager
from craft_parts.plugins import nil_plugin


class TestLifecycleManager:
    """Verify lifecycle manager initialization."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        # pylint: disable=attribute-defined-outside-init
        yaml_data = textwrap.dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )
        self._data = yaml.safe_load(yaml_data)
        # pylint: enable=attribute-defined-outside-init

    def test_invalid_arch(self, new_dir):
        with pytest.raises(errors.InvalidArchitecture) as raised:
            LifecycleManager(
                self._data,
                application_name="test_manager",
                cache_dir=new_dir,
                arch="invalid",
            )
        assert raised.value.arch_name == "invalid"

    @pytest.mark.parametrize("name", ["myapp", "Myapp_2", "MYAPP", "x"])
    def test_application_name(self, new_dir, name):
        lf = LifecycleManager(self._data, application_name=name, cache_dir=new_dir)
        info = lf.project_info
        assert info.application_name == name

    @pytest.mark.parametrize("name", ["", "1", "_", "_myapp", "myapp-2", "myapp_2.1"])
    def test_application_name_invalid(self, new_dir, name):
        with pytest.raises(errors.InvalidApplicationName) as raised:
            LifecycleManager(self._data, application_name=name, cache_dir=new_dir)
        assert raised.value.name == name

    def test_project_info(self, new_dir):
        lf = LifecycleManager(
            self._data,
            application_name="test_manager",
            project_name="project",
            cache_dir=new_dir,
            work_dir="work_dir",
            arch="aarch64",
            parallel_build_count=16,
            custom="foo",
        )
        info = lf.project_info

        assert info.application_name == "test_manager"
        assert info.project_name == "project"
        assert info.target_arch == "arm64"
        assert info.arch_triplet == "aarch64-linux-gnu"
        assert info.parallel_build_count == 16
        assert info.dirs.parts_dir == new_dir / "work_dir" / "parts"
        assert info.dirs.stage_dir == new_dir / "work_dir" / "stage"
        assert info.dirs.prime_dir == new_dir / "work_dir" / "prime"
        assert info.custom_args == ["custom"]
        assert info.custom == "foo"

    def test_part_initialization(self, new_dir, mocker):
        mock_seq = mocker.patch("craft_parts.sequencer.Sequencer")

        lf = LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            ignore_local_sources=["foo.*"],
        )

        assert len(lf._part_list) == 1

        part = lf._part_list[0]
        assert part.name == "foo"
        assert part.plugin == "nil"
        assert isinstance(part.plugin_properties, nil_plugin.NilPluginProperties)

        mock_seq.assert_called_once_with(
            part_list=lf._part_list,
            project_info=lf.project_info,
            ignore_outdated=["foo.*"],
            base_layer_hash=None,
        )

    def test_sequencer_creation(self, new_dir, mocker):
        mock_sequencer = mocker.patch("craft_parts.sequencer.Sequencer")

        LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            ignore_local_sources=["ign1", "ign2"],
            custom="foo",
        )

        assert mock_sequencer.mock_calls == [
            call(
                part_list=[ANY],
                project_info=ANY,
                ignore_outdated=["ign1", "ign2"],
                base_layer_hash=None,
            )
        ]

    def test_executor_creation(self, new_dir, mocker):
        mock_executor = mocker.patch("craft_parts.executor.Executor")

        LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            parallel_build_count=16,
            extra_build_packages=["pkg1", "pkg2"],
            extra_build_snaps=["snap1", "snap2"],
            ignore_local_sources=["ign1", "ign2"],
            custom="foo",
        )

        assert mock_executor.mock_calls == [
            call(
                part_list=[ANY],
                project_info=ANY,
                ignore_patterns=["ign1", "ign2"],
                extra_build_packages=["pkg1", "pkg2"],
                extra_build_snaps=["snap1", "snap2"],
                base_layer_dir=None,
                base_layer_hash=None,
            )
        ]


class TestOverlaySupport:
    """Overlays only supported in linux and must run as root."""

    @pytest.fixture
    def parts_data(self) -> Dict[str, Any]:
        return {"parts": {"foo": {"plugin": "nil", "overlay-script": "ls"}}}

    def test_overlay_supported(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "linux")
        mocker.patch("os.geteuid", return_value=0)
        LifecycleManager(
            parts_data,
            application_name="test",
            cache_dir=new_dir,
            base_layer_dir=new_dir,
            base_layer_hash=b"hash",
        )

    def test_overlay_platform_unsupported(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "darwin")
        mocker.patch("os.geteuid", return_value=0)
        with pytest.raises(errors.OverlayPlatformError):
            LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                base_layer_dir=new_dir,
                base_layer_hash=b"hash",
            )

    def test_overlay_requires_root(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "linux")
        mocker.patch("os.geteuid", return_value=1000)
        with pytest.raises(errors.OverlayPermissionError):
            LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                base_layer_dir=new_dir,
                base_layer_hash=b"hash",
            )


class TestPluginProperties:
    """Verify if plugin properties are correctly handled."""

    def test_plugin_properties(self, new_dir, mocker):
        mocker.patch("craft_parts.sequencer.Sequencer")

        lf = LifecycleManager(
            {
                "parts": {
                    "bar": {
                        "source": ".",
                        "plugin": "make",
                        "make-parameters": ["-DTEST_PARAMETER"],
                    }
                }
            },
            application_name="test_manager",
            cache_dir=new_dir,
        )

        assert len(lf._part_list) == 1
        part = lf._part_list[0]
        assert part.plugin_properties.make_parameters == ["-DTEST_PARAMETER"]

    def test_fallback_plugin_name(self, new_dir, mocker):
        mocker.patch("craft_parts.sequencer.Sequencer")

        lf = LifecycleManager(
            {
                "parts": {
                    "make": {
                        "source": ".",
                        "make-parameters": ["-DTEST_PARAMETER"],
                    }
                }
            },
            application_name="test_manager",
            cache_dir=new_dir,
        )

        assert len(lf._part_list) == 1
        part = lf._part_list[0]
        assert part.plugin_properties.make_parameters == ["-DTEST_PARAMETER"]

    def test_invalid_plugin_name(self, new_dir):
        with pytest.raises(errors.InvalidPlugin) as raised:
            LifecycleManager(
                {
                    "parts": {
                        "bar": {
                            "plugin": "invalid",
                            "make-parameters": ["-DTEST_PARAMETER"],
                        }
                    }
                },
                application_name="test_manager",
                cache_dir=new_dir,
            )
        assert raised.value.part_name == "bar"
        assert raised.value.plugin_name == "invalid"

    def test_undefined_plugin_name(self, new_dir):
        with pytest.raises(errors.UndefinedPlugin) as raised:
            LifecycleManager(
                {
                    "parts": {
                        "bar": {
                            "make-parameters": ["-DTEST_PARAMETER"],
                        }
                    }
                },
                application_name="test_manager",
                cache_dir=new_dir,
            )
        assert raised.value.part_name == "bar"
