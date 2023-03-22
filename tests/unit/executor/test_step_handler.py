# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Set

import pytest

from craft_parts import plugins, sources
from craft_parts.dirs import ProjectDirs
from craft_parts.executor.environment import generate_step_environment
from craft_parts.executor.step_handler import StepContents, StepHandler
from craft_parts.infos import (
    _ARCH_TRANSLATIONS,
    PartInfo,
    ProjectInfo,
    StepInfo,
    _get_host_architecture,
)
from craft_parts.parts import Part
from craft_parts.steps import Step
from tests.unit.common_plugins import StrictTestPlugin


class FooPlugin(plugins.Plugin):
    """A test plugin."""

    properties_class = plugins.PluginProperties

    def get_build_snaps(self) -> Set[str]:
        return set()

    def get_build_packages(self) -> Set[str]:
        return set()

    def get_build_environment(self) -> Dict[str, str]:
        return {}

    def get_build_commands(self) -> List[str]:
        return ["hello"]


def _step_handler_for_step(
    step: Step, cache_dir: Path, strict_mode: bool = False, plugin_class=None
) -> StepHandler:
    p1 = Part("p1", {"source": "."})
    dirs = ProjectDirs()
    info = ProjectInfo(
        project_dirs=dirs,
        application_name="test",
        cache_dir=cache_dir,
        strict_mode=strict_mode,
    )
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=step)
    props = plugins.PluginProperties()
    if plugin_class:
        plugin = plugin_class(properties=props, part_info=part_info)
    else:
        plugin = FooPlugin(properties=props, part_info=part_info)
    source_handler = sources.get_source_handler(
        cache_dir=cache_dir,
        part=p1,
        project_dirs=dirs,
    )
    step_env = generate_step_environment(part=p1, plugin=plugin, step_info=step_info)

    return StepHandler(
        part=p1,
        step_info=step_info,
        plugin=plugin,
        source_handler=source_handler,
        env=step_env,
    )


def get_mode(path) -> int:
    """Shortcut the retrieve the read/write/execute mode for a given path."""
    return os.stat(path).st_mode & 0o777


class TestStepHandlerBuiltins:
    """Verify the built-in handlers."""

    def test_run_builtin_pull(self, new_dir, mocker):
        mock_source_pull = mocker.patch(
            "craft_parts.sources.local_source.LocalSource.pull"
        )

        sh = _step_handler_for_step(Step.PULL, cache_dir=new_dir)
        result = sh.run_builtin()

        mock_source_pull.assert_called_once_with()
        assert result == StepContents()

    def test_run_builtin_overlay(self, new_dir, mocker):
        sh = _step_handler_for_step(Step.OVERLAY, cache_dir=new_dir)
        result = sh.run_builtin()
        assert result == StepContents()

    def test_run_builtin_build(self, new_dir, mocker):
        mock_run = mocker.patch("subprocess.run")

        Path("parts/p1/run").mkdir(parents=True)
        sh = _step_handler_for_step(Step.BUILD, cache_dir=new_dir)
        result = sh.run_builtin()
        build_script_path = Path(new_dir / "parts/p1/run/build.sh")
        environment_script_path = Path(new_dir / "parts/p1/run/environment.sh")
        host_arch = _ARCH_TRANSLATIONS[_get_host_architecture()]

        assert get_mode(environment_script_path) == 0o644
        with open(environment_script_path, "r") as file:
            assert file.read() == dedent(
                f"""\
                # Environment
                ## Application environment
                ## Part environment
                export CRAFT_ARCH_TRIPLET="{host_arch['triplet']}"
                export CRAFT_TARGET_ARCH="{host_arch['deb']}"
                export CRAFT_PARALLEL_BUILD_COUNT="1"
                export CRAFT_PROJECT_DIR="{new_dir}"
                export CRAFT_STAGE="{new_dir}/stage"
                export CRAFT_PRIME="{new_dir}/prime"
                export CRAFT_PART_NAME="p1"
                export CRAFT_STEP_NAME="BUILD"
                export CRAFT_PART_SRC="{new_dir}/parts/p1/src"
                export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"
                export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"
                export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"
                export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"
                ## Plugin environment
                ## User environment
                """
            )

        assert get_mode(build_script_path) == 0o755
        with open(build_script_path, "r") as file:
            assert file.read() == dedent(
                f"""\
                #!/bin/bash
                set -euo pipefail
                source {environment_script_path}
                set -x
                hello
                """
            )

        mock_run.assert_called_once_with(
            [build_script_path],
            cwd=Path(new_dir / "parts/p1/build"),
            check=True,
            stdout=None,
            stderr=None,
        )
        assert result == StepContents()

    def test_run_builtin_stage(self, new_dir, mocker):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage").mkdir()
        sh = _step_handler_for_step(Step.STAGE, cache_dir=new_dir)
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_prime(self, new_dir, mocker):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage/subdir").mkdir(parents=True)
        Path("stage/foo").write_text("content")
        Path("stage/subdir/bar").write_text("content")
        sh = _step_handler_for_step(Step.PRIME, cache_dir=new_dir)
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_invalid(self, new_dir):
        sh = _step_handler_for_step(999, cache_dir=new_dir)  # type: ignore
        with pytest.raises(RuntimeError) as raised:
            sh.run_builtin()
        assert str(raised.value) == (
            "Request to run the built-in handler for an invalid step."
        )

    def test_run_builtin_pull_strict(self, new_dir, mocker):
        """Test the Pull step in strict mode calls get_pull_commands()"""
        Path("parts/p1/run").mkdir(parents=True)
        mock_run = mocker.patch("subprocess.run")
        sh = _step_handler_for_step(
            Step.PULL,
            cache_dir=new_dir,
            strict_mode=True,
            plugin_class=StrictTestPlugin,
        )

        sh.run_builtin()

        # Check that when StrictTestPlugin.get_pull_commands() is called
        # 'strict mode' is correctly enabled.
        assert mock_run.called
        run_args = mock_run.call_args[0][0]
        script_path = run_args[0]
        assert "strict mode: True" in script_path.read_text()


class TestStepHandlerRunScriptlet:
    """Verify the scriptlet runner."""

    def test_run_scriptlet(self, new_dir, capfd):
        sh = _step_handler_for_step(Step.PULL, cache_dir=new_dir)
        sh.run_scriptlet(
            "echo hello world", scriptlet_name="name", step=Step.BUILD, work_dir=new_dir
        )
        captured = capfd.readouterr()
        assert captured.out == "hello world\n"

    # TODO: test ctl api server
