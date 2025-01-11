# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021,2024 Canonical Ltd.
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
import itertools
import os
from pathlib import Path
from textwrap import dedent

import pytest
from craft_parts import errors, plugins, sources
from craft_parts.dirs import ProjectDirs
from craft_parts.executor.environment import generate_step_environment
from craft_parts.executor.step_handler import StepContents, StepHandler
from craft_parts.infos import (
    _DEB_TO_TRIPLET,
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

    def get_build_snaps(self) -> set[str]:
        return set()

    def get_build_packages(self) -> set[str]:
        return set()

    def get_build_environment(self) -> dict[str, str]:
        return {}

    def get_build_commands(self) -> list[str]:
        return ["hello"]


def _step_handler_for_step(
    step: Step,
    cache_dir: Path,
    part_info: PartInfo,
    part: Part,
    dirs: ProjectDirs,
    plugin_class: type[plugins.Plugin] = FooPlugin,
    partitions: set[str] | None = None,
) -> StepHandler:
    step_info = StepInfo(part_info=part_info, step=step)
    props = plugins.PluginProperties()
    plugin = plugin_class(properties=props, part_info=part_info)
    source_handler = sources.get_source_handler(
        cache_dir=cache_dir,
        part=part,
        project_dirs=dirs,
    )
    step_env = generate_step_environment(part=part, plugin=plugin, step_info=step_info)

    return StepHandler(
        part=part,
        step_info=step_info,
        plugin=plugin,
        source_handler=source_handler,
        env=step_env,
        partitions=partitions,
    )


def get_mode(path) -> int:
    """Shortcut the retrieve the read/write/execute mode for a given path."""
    return os.stat(path).st_mode & 0o777


class TestStepHandlerBuiltins:
    """Verify the built-in handlers."""

    @pytest.fixture(autouse=True)
    def setup(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._partitions = partitions
        self._part = Part("p1", {"source": "."}, partitions=partitions)
        self._dirs = ProjectDirs(partitions=partitions)
        self._project_info = ProjectInfo(
            project_dirs=self._dirs,
            application_name="test",
            cache_dir=new_dir,
            strict_mode=False,
            partitions=self._partitions,
        )
        self._part_info = PartInfo(project_info=self._project_info, part=self._part)
        self._props = plugins.PluginProperties()
        # pylint: enable=attribute-defined-outside-init

    def test_run_builtin_pull(self, new_dir, mocker):
        mock_source_pull = mocker.patch(
            "craft_parts.sources.local_source.LocalSource.pull"
        )

        sh = _step_handler_for_step(
            Step.PULL,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        result = sh.run_builtin()

        mock_source_pull.assert_called_once_with()
        assert result == StepContents()

    def test_run_builtin_overlay(self, new_dir, mocker):
        sh = _step_handler_for_step(
            Step.OVERLAY,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        result = sh.run_builtin()
        assert result == StepContents()

    def test_run_builtin_build(self, new_dir, partitions, mocker):
        mock_run = mocker.patch("craft_parts.utils.process.run")

        Path("parts/p1/run").mkdir(parents=True)
        sh = _step_handler_for_step(
            Step.BUILD,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        result = sh.run_builtin()
        build_script_path = Path(new_dir / "parts/p1/run/build.sh")
        environment_script_path = Path(new_dir / "parts/p1/run/environment.sh")
        deb = _get_host_architecture()
        triplet = _DEB_TO_TRIPLET[deb]
        if partitions is not None:
            partition_script_lines = [
                f'export CRAFT_DEFAULT_STAGE="{new_dir}/stage"',
                f'export CRAFT_DEFAULT_PRIME="{new_dir}/prime"',
                *itertools.chain.from_iterable(
                    zip(
                        [
                            f'export CRAFT_{p.upper().translate({ord("-"): "_", ord("/"): "_"})}_STAGE="{new_dir}/partitions/{p}/stage"'
                            for p in partitions
                            if p != "default"
                        ],
                        [
                            f'export CRAFT_{p.upper().translate({ord("-"): "_", ord("/"): "_"})}_PRIME="{new_dir}/partitions/{p}/prime"'
                            for p in partitions
                            if p != "default"
                        ],
                    )
                ),
            ]
        else:
            partition_script_lines = []

        expected_script = "\n".join(
            (
                "# Environment",
                "## Application environment",
                "## Part environment",
                f'export CRAFT_ARCH_TRIPLET="{triplet}"',
                f'export CRAFT_TARGET_ARCH="{deb}"',
                f'export CRAFT_ARCH_BUILD_ON="{deb}"',
                f'export CRAFT_ARCH_BUILD_FOR="{deb}"',
                f'export CRAFT_ARCH_TRIPLET_BUILD_ON="{triplet}"',
                f'export CRAFT_ARCH_TRIPLET_BUILD_FOR="{triplet}"',
                'export CRAFT_PARALLEL_BUILD_COUNT="1"',
                f'export CRAFT_PROJECT_DIR="{new_dir}"',
                *partition_script_lines,
                f'export CRAFT_STAGE="{new_dir}/stage"',
                f'export CRAFT_PRIME="{new_dir}/prime"',
                'export CRAFT_PART_NAME="p1"',
                'export CRAFT_STEP_NAME="BUILD"',
                f'export CRAFT_PART_SRC="{new_dir}/parts/p1/src"',
                f'export CRAFT_PART_SRC_WORK="{new_dir}/parts/p1/src"',
                f'export CRAFT_PART_BUILD="{new_dir}/parts/p1/build"',
                f'export CRAFT_PART_BUILD_WORK="{new_dir}/parts/p1/build"',
                f'export CRAFT_PART_INSTALL="{new_dir}/parts/p1/install"',
                "## Plugin environment",
                "## User environment",
                "",
            )
        )

        assert get_mode(environment_script_path) == 0o644
        with open(environment_script_path) as file:
            assert file.read() == expected_script

        assert get_mode(build_script_path) == 0o755
        with open(build_script_path) as file:
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
            selector=None,
        )
        assert result == StepContents()

    def test_run_builtin_stage(self, new_dir, partitions):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage").mkdir()
        sh = _step_handler_for_step(
            Step.STAGE,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
            partitions=partitions,
        )
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_prime(self, new_dir, partitions):
        Path("parts/p1/install").mkdir(parents=True)
        Path("parts/p1/install/subdir").mkdir(parents=True)
        Path("parts/p1/install/foo").write_text("content")
        Path("parts/p1/install/subdir/bar").write_text("content")
        Path("stage/subdir").mkdir(parents=True)
        Path("stage/foo").write_text("content")
        Path("stage/subdir/bar").write_text("content")
        sh = _step_handler_for_step(
            Step.PRIME,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
            partitions=partitions,
        )
        result = sh.run_builtin()

        assert result == StepContents(files={"subdir/bar", "foo"}, dirs={"subdir"})

    def test_run_builtin_invalid(self, new_dir):
        sh = _step_handler_for_step(
            999,  # type: ignore[reportGeneralTypeIssues]
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        with pytest.raises(RuntimeError) as raised:
            sh.run_builtin()
        assert str(raised.value) == (
            "Request to run the built-in handler for an invalid step."
        )

    def test_run_builtin_pull_strict(self, new_dir, mocker):
        """Test the Pull step in strict mode calls get_pull_commands()"""
        Path("parts/p1/run").mkdir(parents=True)
        mock_run = mocker.patch("craft_parts.utils.process.run")
        self._project_info._strict_mode = True
        sh = _step_handler_for_step(
            Step.PULL,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
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

    @pytest.fixture(autouse=True)
    def setup(self, new_dir, partitions):
        # pylint: disable=attribute-defined-outside-init
        self._part = Part("p1", {"source": "."}, partitions=partitions)
        self._dirs = ProjectDirs(partitions=partitions)
        self._project_info = ProjectInfo(
            project_dirs=self._dirs,
            application_name="test",
            cache_dir=new_dir,
            strict_mode=False,
            partitions=partitions,
        )
        self._part_info = PartInfo(project_info=self._project_info, part=self._part)
        self._props = plugins.PluginProperties()
        # pylint: enable=attribute-defined-outside-init

    def test_run_scriptlet(self, new_dir, capfd):
        sh = _step_handler_for_step(
            Step.BUILD,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        sh.run_scriptlet(
            "echo hello world", scriptlet_name="name", step=Step.BUILD, work_dir=new_dir
        )
        captured = capfd.readouterr()
        assert captured.out == "hello world\n"

    def test_run_scriptlet_error(self, new_dir, capfd):
        sh = _step_handler_for_step(
            Step.BUILD,
            cache_dir=new_dir,
            part_info=self._part_info,
            part=self._part,
            dirs=self._dirs,
        )
        with pytest.raises(errors.ScriptletRunError) as raised:
            sh.run_scriptlet(
                "echo uh-oh>&2;false",
                scriptlet_name="name",
                step=Step.BUILD,
                work_dir=new_dir,
            )
        assert raised.value.stderr is not None
        assert raised.value.stderr.endswith(b"\nuh-oh\n+ false\n")

    # TODO: test ctl api server
