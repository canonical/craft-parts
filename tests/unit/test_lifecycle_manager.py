# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2023 Canonical Ltd.
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
from pathlib import Path
from typing import Any
from unittest.mock import ANY, call

import craft_parts
import craft_parts.utils.partition_utils
import pytest
import yaml
from craft_parts import errors, lifecycle_manager
from craft_parts.plugins import nil_plugin
from craft_parts.state_manager import states

from tests.unit.common_plugins import NonStrictTestPlugin, StrictTestPlugin


@pytest.fixture
def mock_available_plugins(monkeypatch):
    available = {"strict": StrictTestPlugin, "nonstrict": NonStrictTestPlugin}
    monkeypatch.setattr(craft_parts.plugins.plugins, "_PLUGINS", available)


def create_data(part_name: str, plugin_name: str) -> dict[str, Any]:
    return {"parts": {part_name: {"plugin": plugin_name}}}


class TestLifecycleManager:
    """Verify lifecycle manager initialization."""

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self) -> None:
        # pylint: disable=attribute-defined-outside-init
        yaml_data = textwrap.dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )
        self._data = yaml.safe_load(yaml_data)
        self._lcm_kwargs: dict[str, Any] = {}
        # pylint: enable=attribute-defined-outside-init

    def test_invalid_arch(self, new_dir):
        with pytest.raises(errors.InvalidArchitecture) as raised:
            lifecycle_manager.LifecycleManager(
                self._data,
                application_name="test_manager",
                cache_dir=new_dir,
                arch="invalid",
                **self._lcm_kwargs,
            )
        assert raised.value.arch_name == "invalid"

    @pytest.mark.parametrize("name", ["myapp", "Myapp_2", "MYAPP", "x"])
    def test_application_name(self, new_dir, name):
        lf = lifecycle_manager.LifecycleManager(
            self._data, application_name=name, cache_dir=new_dir, **self._lcm_kwargs
        )
        info = lf.project_info
        assert info.application_name == name

    @pytest.mark.parametrize("name", ["", "1", "_", "_myapp", "myapp-2", "myapp_2.1"])
    def test_application_name_invalid(self, new_dir, name):
        with pytest.raises(errors.InvalidApplicationName) as raised:
            lifecycle_manager.LifecycleManager(
                self._data, application_name=name, cache_dir=new_dir
            )
        assert raised.value.name == name

    def test_part_dependency_name_invalid(self, new_dir):
        self._data["parts"]["foo"]["after"] = ["trololo"]
        with pytest.raises(errors.InvalidPartName) as raised:
            lifecycle_manager.LifecycleManager(
                self._data,
                application_name="test",
                cache_dir=new_dir,
                **self._lcm_kwargs,
            )
        assert raised.value.part_name == "trololo"

    @pytest.mark.parametrize("work_dir", [".", "work_dir"])
    def test_project_info(self, new_dir, work_dir):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            project_name="project",
            cache_dir=new_dir,
            work_dir=work_dir,
            arch="arm64",
            parallel_build_count=16,
            custom="foo",
            **self._lcm_kwargs,
        )
        info = lf.project_info

        assert info.application_name == "test_manager"
        assert info.project_name == "project"
        assert info.target_arch == "arm64"
        assert info.arch_triplet == "aarch64-linux-gnu"
        assert info.parallel_build_count == 16
        assert info.dirs.parts_dir == new_dir / work_dir / "parts"
        assert info.dirs.stage_dir == new_dir / work_dir / "stage"
        assert info.dirs.prime_dir == new_dir / work_dir / "prime"
        assert info.custom_args == ["custom"]
        assert info.custom == "foo"

    @pytest.mark.parametrize(
        ("base_layer_dir", "base_layer_hash"),
        [(None, None), (Path("base"), b"deadbeef")],
    )
    def test_project_info_base_layer(self, new_dir, base_layer_dir, base_layer_hash):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            base_layer_dir=base_layer_dir,
            base_layer_hash=base_layer_hash,
            **self._lcm_kwargs,
        )
        info = lf.project_info

        assert info.base_layer_dir == base_layer_dir
        assert info.base_layer_hash == base_layer_hash

    def test_part_initialization(self, new_dir, mocker):
        mock_seq = mocker.patch("craft_parts.sequencer.Sequencer")

        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            ignore_local_sources=["foo.*"],
            **self._lcm_kwargs,
        )

        assert len(lf._part_list) == 1

        part = lf._part_list[0]
        assert part.name == "foo"
        assert part.plugin_name == "nil"
        assert isinstance(part.plugin_properties, nil_plugin.NilPluginProperties)

        mock_seq.assert_called_once_with(
            part_list=lf._part_list,
            project_info=lf.project_info,
            ignore_outdated=["foo.*"],
            base_layer_hash=None,
        )

    def test_sequencer_creation(self, new_dir, mocker):
        mock_sequencer = mocker.patch("craft_parts.sequencer.Sequencer")

        lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            ignore_local_sources=["ign1", "ign2"],
            custom="foo",
            **self._lcm_kwargs,
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

        lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            parallel_build_count=16,
            extra_build_packages=["pkg1", "pkg2"],
            extra_build_snaps=["snap1", "snap2"],
            ignore_local_sources=["ign1", "ign2"],
            custom="foo",
            **self._lcm_kwargs,
        )

        assert mock_executor.mock_calls == [
            call(
                part_list=[ANY],
                project_info=ANY,
                ignore_patterns=["ign1", "ign2"],
                extra_build_packages=["pkg1", "pkg2"],
                extra_build_snaps=["snap1", "snap2"],
                track_stage_packages=False,
                base_layer_dir=None,
                base_layer_hash=None,
            )
        ]

    def test_get_primed_stage_packages(self, new_dir):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            **self._lcm_kwargs,
        )

        state = states.PrimeState(primed_stage_packages={"pkg2==2", "pkg1==1"})
        state.write(Path(new_dir, "parts/foo/state/prime"))

        assert lf.get_primed_stage_packages(part_name="foo") == ["pkg1==1", "pkg2==2"]

    def test_get_primed_stage_packages_no_state(self, new_dir):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            **self._lcm_kwargs,
        )
        assert lf.get_primed_stage_packages(part_name="foo") is None

    def test_get_pull_assets(self, new_dir):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            **self._lcm_kwargs,
        )

        state = states.PullState(assets={"asset1": "val1", "asset2": "val2"})
        state.write(Path(new_dir, "parts/foo/state/pull"))

        assert lf.get_pull_assets(part_name="foo") == {
            "asset1": "val1",
            "asset2": "val2",
        }

    def test_get_pull_assets_no_state(self, new_dir):
        lf = lifecycle_manager.LifecycleManager(
            self._data,
            application_name="test_manager",
            cache_dir=new_dir,
            **self._lcm_kwargs,
        )
        assert lf.get_pull_assets(part_name="foo") is None

    def test_strict_plugins(self, new_dir, mock_available_plugins):
        """Test using a strict plugin in strict mode."""
        data = create_data("p1", "strict")
        lf = lifecycle_manager.LifecycleManager(
            data,
            application_name="test_manager",
            cache_dir=new_dir,
            strict_mode=True,
            **self._lcm_kwargs,
        )
        assert lf.get_pull_assets(part_name="p1") is None

    def test_strict_plugins_error(self, new_dir, mock_available_plugins):
        """Test that using a non-strict plugin in strict mode is an error."""
        data = create_data("p1", "nonstrict")
        with pytest.raises(errors.PluginNotStrict) as exc:
            lifecycle_manager.LifecycleManager(
                data,
                application_name="test_manager",
                cache_dir=new_dir,
                strict_mode=True,
                **self._lcm_kwargs,
            )
        assert "p1" in str(exc.value)


class TestOverlayDisabled:
    """Overlays only supported in linux and must run as root."""

    @pytest.fixture
    def parts_data(self) -> dict[str, Any]:
        return {"parts": {"foo": {"plugin": "nil", "overlay-script": "ls"}}}

    def test_overlay_supported(self, mocker, new_dir, parts_data):
        mocker.patch.object(sys, "platform", "linux")
        mocker.patch("os.geteuid", return_value=0)
        with pytest.raises(errors.PartSpecificationError) as raised:
            lifecycle_manager.LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                base_layer_dir=new_dir,
                base_layer_hash=b"hash",
            )
        assert raised.value.part_name == "foo"
        assert (
            raised.value.message
            == "- Value error, overlays not supported in field 'overlay-script'"
        )


class TestPartitionsDisabled:
    """Partition feature must be enabled when partition are defined."""

    @pytest.fixture
    def parts_data(self) -> dict[str, Any]:
        return {"parts": {"foo": {"plugin": "nil"}}}

    def test_partitions_disabled(self, new_dir, parts_data):
        with pytest.raises(errors.FeatureError) as raised:
            lifecycle_manager.LifecycleManager(
                parts_data,
                application_name="test",
                cache_dir=new_dir,
                partitions=["default"],
            )
        assert (
            raised.value.message
            == "Partitions are defined but partition feature is not enabled."
        )


class TestPluginProperties:
    """Verify if plugin properties are correctly handled."""

    def _get_manager(self, new_dir, **kwargs):
        manager_kwargs = {
            "application_name": "test_manager",
            "cache_dir": new_dir,
        }
        manager_kwargs.update(kwargs)
        return lifecycle_manager.LifecycleManager(**manager_kwargs)

    def test_plugin_properties(self, new_dir, mocker):
        mocker.patch("craft_parts.sequencer.Sequencer")

        lf = self._get_manager(
            new_dir,
            all_parts={
                "parts": {
                    "bar": {
                        "source": ".",
                        "plugin": "make",
                        "make-parameters": ["-DTEST_PARAMETER"],
                    }
                }
            },
        )

        assert len(lf._part_list) == 1
        part = lf._part_list[0]
        assert part.plugin_properties.make_parameters == ["-DTEST_PARAMETER"]

    def test_fallback_plugin_name(self, new_dir, mocker):
        mocker.patch("craft_parts.sequencer.Sequencer")

        lf = self._get_manager(
            new_dir,
            all_parts={
                "parts": {
                    "make": {
                        "source": ".",
                        "make-parameters": ["-DTEST_PARAMETER"],
                    }
                }
            },
        )

        assert len(lf._part_list) == 1
        part = lf._part_list[0]
        assert part.plugin_properties.make_parameters == ["-DTEST_PARAMETER"]

    def test_invalid_plugin_name(self, new_dir):
        with pytest.raises(errors.InvalidPlugin) as raised:
            self._get_manager(
                new_dir,
                all_parts={
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
            self._get_manager(
                new_dir,
                all_parts={
                    "parts": {
                        "bar": {
                            "make-parameters": ["-DTEST_PARAMETER"],
                        }
                    }
                },
            )
        assert raised.value.part_name == "bar"

    def test_unsupported_build_attributes(self, new_dir):
        with pytest.raises(errors.UnsupportedBuildAttributesError):
            self._get_manager(
                new_dir,
                all_parts={
                    "parts": {
                        "bar": {"plugin": "nil", "build-attributes": ["self-contained"]}
                    }
                },
            )
