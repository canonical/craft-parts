# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2022 Canonical Ltd.
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

"""Handle the execution of built-in or user specified step commands."""

import dataclasses
import functools
import json
import logging
import os
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Set, TextIO, Union

from craft_parts import errors, packages
from craft_parts.infos import StepInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin
from craft_parts.sources import SourceHandler
from craft_parts.steps import Step
from craft_parts.utils import file_utils

from . import filesets
from .filesets import Fileset
from .migration import migrate_files

logger = logging.getLogger(__name__)

Stream = Optional[Union[TextIO, int]]


@dataclasses.dataclass(frozen=True)
class StepContents:
    """Files and directories to be added to the step's state."""

    files: Set[str] = dataclasses.field(default_factory=set)
    dirs: Set[str] = dataclasses.field(default_factory=set)


class StepHandler:
    """Executes built-in or user-specified step commands.

    The step handler takes care of the execution of a step, using either
    a built-in set of actions to be taken, or executing a user-defined
    script defined in the part specification User-defined scripts may also
    call the built-in handler for a step by invoking a control utility.
    This class implements the built-in handlers and a FIFO-based mechanism
    and API to be used by the external control utility to communicate with
    the running instance.
    """

    def __init__(
        self,
        part: Part,
        *,
        step_info: StepInfo,
        plugin: Plugin,
        source_handler: Optional[SourceHandler],
        env: str,
        stdout: Stream = None,
        stderr: Stream = None,
    ):
        self._part = part
        self._step_info = step_info
        self._plugin = plugin
        self._source_handler = source_handler
        self._env = env
        self._stdout = stdout
        self._stderr = stderr

    def run_builtin(self) -> StepContents:
        """Run the built-in commands for the current step."""
        step = self._step_info.step

        if step == Step.PULL:
            handler = self._builtin_pull
        elif step == Step.OVERLAY:
            handler = self._builtin_overlay
        elif step == Step.BUILD:
            handler = self._builtin_build
        elif step == Step.STAGE:
            handler = self._builtin_stage
        elif step == Step.PRIME:
            handler = self._builtin_prime
        else:
            raise RuntimeError(
                "Request to run the built-in handler for an invalid step."
            )

        return handler()

    def _builtin_pull(self) -> StepContents:
        if self._source_handler:
            self._source_handler.pull()
        return StepContents()

    @staticmethod
    def _builtin_overlay() -> StepContents:
        return StepContents()

    def _builtin_build(self) -> StepContents:

        # Plugin commands.
        plugin_build_commands = self._plugin.get_build_commands()

        # Save script to execute.
        build_script_path = self._part.part_run_dir.absolute() / "build.sh"
        with build_script_path.open("w") as run_file:
            print(self._env, file=run_file)
            print("set -x", file=run_file)

            for build_command in plugin_build_commands:
                print(build_command, file=run_file)

        build_script_path.chmod(0o755)

        try:
            subprocess.run(
                [str(build_script_path)],
                cwd=self._part.part_build_subdir,
                check=True,
                stdout=self._stdout,
                stderr=self._stderr,
            )
        except subprocess.CalledProcessError as process_error:
            raise errors.PluginBuildError(part_name=self._part.name) from process_error

        return StepContents()

    def _builtin_stage(self) -> StepContents:
        stage_fileset = Fileset(self._part.spec.stage_files, name="stage")
        srcdir = str(self._part.part_install_dir)
        files, dirs = filesets.migratable_filesets(stage_fileset, srcdir)

        def pkgconfig_fixup(file_path):
            if os.path.islink(file_path):
                return
            if not file_path.endswith(".pc"):
                return
            packages.fix_pkg_config(
                prefix_prepend=self._part.stage_dir,
                pkg_config_file=file_path,
                prefix_trim=self._part.part_install_dir,
            )

        files, dirs = migrate_files(
            files=files,
            dirs=dirs,
            srcdir=self._part.part_install_dir,
            destdir=self._part.stage_dir,
            fixup_func=pkgconfig_fixup,
        )
        return StepContents(files, dirs)

    def _builtin_prime(self) -> StepContents:
        prime_fileset = Fileset(self._part.spec.prime_files, name="prime")

        # If we're priming and we don't have an explicit set of files to prime
        # include the files from the stage step
        if prime_fileset.entries == ["*"] or len(prime_fileset.includes) == 0:
            stage_fileset = Fileset(self._part.spec.stage_files, name="stage")
            prime_fileset.combine(stage_fileset)

        srcdir = str(self._part.part_install_dir)
        files, dirs = filesets.migratable_filesets(prime_fileset, srcdir)
        files, dirs = migrate_files(
            files=files,
            dirs=dirs,
            srcdir=self._part.stage_dir,
            destdir=self._part.prime_dir,
        )
        # TODO: handle elf dependencies

        return StepContents(files, dirs)

    def run_scriptlet(
        self,
        scriptlet: str,
        *,
        scriptlet_name: str,
        step: Step,
        work_dir: Path,
    ) -> None:
        """Execute a scriptlet.

        :param scriptlet: the scriptlet to run.
        :param work_dir: the directory where the script will be executed.
        """
        with tempfile.TemporaryDirectory() as tempdir:
            call_fifo = file_utils.NonBlockingRWFifo(
                os.path.join(tempdir, "function_call")
            )
            feedback_fifo = file_utils.NonBlockingRWFifo(
                os.path.join(tempdir, "call_feedback")
            )

            script = textwrap.dedent(
                f"""\
                set -euo pipefail
                export PARTS_CALL_FIFO={call_fifo.path}
                export PARTS_FEEDBACK_FIFO={feedback_fifo.path}

                {self._env}

                set -x
                {scriptlet}"""
            )

            # FIXME: refactor ctl protocol server

            with tempfile.TemporaryFile(mode="w+") as script_file:
                print(script, file=script_file)
                script_file.flush()
                script_file.seek(0)
                process = subprocess.Popen(  # pylint: disable=consider-using-with
                    ["/bin/bash"],
                    stdin=script_file,
                    cwd=work_dir,
                    stdout=self._stdout,
                    stderr=self._stderr,
                )

            status = None
            try:
                while status is None:
                    function_call = call_fifo.read()
                    if not function_call:
                        status = process.poll()
                        time.sleep(0.1)  # Don't loop TOO busily
                        continue

                    # Handle the function and send feedback to caller.
                    try:
                        retval = self._handle_control_api(
                            step, scriptlet_name, function_call.strip()
                        )
                        feedback_fifo.write(f"OK {retval!s}\n" if retval else "OK\n")
                    except errors.PartsError as error:
                        feedback_fifo.write(f"ERR {error!s}\n")

            except Exception as error:
                logger.debug("scriptlet execution failed: %s", error)
                raise error
            finally:
                call_fifo.close()
                feedback_fifo.close()

            if process.returncode != 0:
                raise errors.ScriptletRunError(
                    part_name=self._part.name,
                    scriptlet_name=scriptlet_name,
                    exit_code=status,
                )

    def _handle_control_api(
        self, step: Step, scriptlet_name: str, function_call: str
    ) -> str:
        """Parse the command message received from the client."""
        try:
            function_json = json.loads(function_call)
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                f"{scriptlet_name!r} scriptlet called a function with invalid json: "
                f"{function_call}"
            ) from err

        for attr in ["function", "args"]:
            if attr not in function_json:
                raise RuntimeError(
                    f"{scriptlet_name!r} control call missing attribute {attr!r}"
                )

        cmd_name = function_json["function"]
        cmd_args = function_json["args"]

        return self._process_api_commands(
            cmd_name, cmd_args, step=step, scriptlet_name=scriptlet_name
        )

    def _process_api_commands(
        self, cmd_name: str, cmd_args: List[str], *, step: Step, scriptlet_name: str
    ) -> str:
        """Invoke API command actions."""
        retval = ""

        invalid_control_api_call = functools.partial(
            errors.InvalidControlAPICall,
            part_name=self._part.name,
            scriptlet_name=scriptlet_name,
        )

        if cmd_name == "default":
            if len(cmd_args) > 0:
                raise invalid_control_api_call(
                    message=f"invalid arguments to command {cmd_name!r}",
                )
            self._execute_builtin_handler(step)
        elif cmd_name == "set":
            if len(cmd_args) != 1:
                raise invalid_control_api_call(
                    message=(f"invalid arguments to command {cmd_name!r}"),
                )

            if "=" not in cmd_args[0]:
                raise invalid_control_api_call(
                    message=(
                        f"invalid arguments to command {cmd_name!r} (want key=value)"
                    ),
                )

            name, value = cmd_args[0].split("=")

            try:
                self._step_info.set_project_var(name, value)
            except (ValueError, RuntimeError) as err:
                raise errors.InvalidControlAPICall(
                    part_name=self._part.name,
                    scriptlet_name=scriptlet_name,
                    message=str(err),
                )
        elif cmd_name == "get":
            if len(cmd_args) != 1:
                raise invalid_control_api_call(
                    message=(f"invalid number of arguments to command {cmd_name!r}"),
                )
            (name,) = cmd_args

            try:
                retval = self._step_info.get_project_var(name, raw_read=True)
            except ValueError as err:
                raise errors.InvalidControlAPICall(
                    part_name=self._part.name,
                    scriptlet_name=scriptlet_name,
                    message=str(err),
                )
        else:
            raise invalid_control_api_call(
                message=f"invalid command {cmd_name!r}",
            )

        return retval

    def _execute_builtin_handler(self, step: Step) -> None:
        if step == Step.PULL:
            self._builtin_pull()
        elif step == Step.OVERLAY:
            self._builtin_overlay()
        elif step == Step.BUILD:
            self._builtin_build()
        elif step == Step.STAGE:
            self._builtin_stage()
        elif step == Step.PRIME:
            self._builtin_prime()
