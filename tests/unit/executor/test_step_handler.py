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

from pathlib import Path
from typing import Dict, List, Set

import pytest

from craft_parts import plugins, sources
from craft_parts.dirs import ProjectDirs
from craft_parts.executor.environment import generate_step_environment
from craft_parts.executor.step_handler import StepContents, StepHandler
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.parts import Part
from craft_parts.steps import Step


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


def _step_handler_for_step(step: Step, cache_dir: Path) -> StepHandler:
    p1 = Part("p1", {"source": "."})
    dirs = ProjectDirs()
    info = ProjectInfo(project_dirs=dirs, application_name="test", cache_dir=cache_dir)
    part_info = PartInfo(project_info=info, part=p1)
    step_info = StepInfo(part_info=part_info, step=step)
    props = plugins.PluginProperties()
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

        mock_run.assert_called_once_with(
            [str(new_dir / "parts/p1/run/build.sh")],
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


class TestStepHandlerRunScriptlet:
    """Verify the scriptlet runner."""

    def test_run_scriptlet(self, new_dir, capfd):
        sh = _step_handler_for_step(Step.PULL, cache_dir=new_dir)
        sh.run_scriptlet("echo hello world", scriptlet_name="name", work_dir=new_dir)
        captured = capfd.readouterr()
        assert captured.out == "hello world\n"

    # TODO: test ctl api server
