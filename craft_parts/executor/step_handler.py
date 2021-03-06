# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016-2021 Canonical Ltd.
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

"""Handle the execution of built-in or user specified step commands."""

import fileinput
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from collections import namedtuple
from pathlib import Path
from typing import List, Optional, Set, Union

from craft_parts import errors
from craft_parts.executor import collisions
from craft_parts.infos import StepInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin
from craft_parts.sources import SourceHandler
from craft_parts.steps import Step
from craft_parts.utils import file_utils

from . import environment, filesets
from .filesets import Fileset

FilesAndDirs = namedtuple("FilesAndDirs", ["files", "dirs"])


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
    ):
        self._part = part
        self._step_info = step_info
        self._plugin = plugin
        self._source_handler = source_handler
        self._env = environment.generate_part_environment(
            part=part, plugin=plugin, step_info=step_info
        )

    def run_builtin(self) -> FilesAndDirs:
        """Run the built-in commands for the current step."""
        step = self._step_info.step
        if step == Step.PULL:
            handler = self._builtin_pull
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

    def _builtin_pull(self) -> FilesAndDirs:
        if self._source_handler:
            self._source_handler.pull()
        return FilesAndDirs(set(), set())

    def _builtin_build(self) -> FilesAndDirs:

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
                [build_script_path], check=True, cwd=self._part.part_build_subdir
            )
        except subprocess.CalledProcessError as process_error:
            raise errors.PluginBuildError(part_name=self._part.name) from process_error

        return FilesAndDirs(set(), set())

    def _builtin_stage(self) -> FilesAndDirs:
        stage_fileset = Fileset(self._part.spec.stage_files, name="stage")
        srcdir = str(self._part.part_install_dir)
        files, dirs = filesets.migratable_filesets(stage_fileset, srcdir)

        def pkgconfig_fixup(file_path):
            if os.path.islink(file_path):
                return
            if not file_path.endswith(".pc"):
                return
            _fix_pkg_config(
                root=self._part.stage_dir,
                pkg_config_file=file_path,
                prefix_trim=self._part.part_install_dir,
            )

        _migrate_files(
            files=files,
            dirs=dirs,
            srcdir=str(self._part.part_install_dir),
            destdir=str(self._part.stage_dir),
            fixup_func=pkgconfig_fixup,
        )
        return FilesAndDirs(files, dirs)

    def _builtin_prime(self) -> FilesAndDirs:
        prime_fileset = Fileset(self._part.spec.prime_files, name="prime")

        # If we're priming and we don't have an explicit set of files to prime
        # include the files from the stage step
        if prime_fileset.entries == ["*"] or len(prime_fileset.includes) == 0:
            stage_fileset = Fileset(self._part.spec.stage_files, name="stage")
            prime_fileset.combine(stage_fileset)

        srcdir = str(self._part.part_install_dir)
        files, dirs = filesets.migratable_filesets(prime_fileset, srcdir)
        _migrate_files(
            files=files,
            dirs=dirs,
            srcdir=str(self._part.stage_dir),
            destdir=str(self._part.prime_dir),
        )
        # TODO: handle elf dependencies

        return FilesAndDirs(files, dirs)

    def run_scriptlet(
        self, scriptlet: str, *, scriptlet_name: str, work_dir: Path
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

            # the ctl client only works consistently if it's using the exact same
            # interpreter as that used by the server, thus the definition of
            # PARTS_INTERPRETER.
            script = textwrap.dedent(
                """\
                set -e
                export PARTS_CALL_FIFO={call_fifo}
                export PARTS_FEEDBACK_FIFO={feedback_fifo}
                export PARTS_INTERPRETER={interpreter}

                {env}

                {scriptlet}"""
            ).format(
                interpreter=sys.executable,
                call_fifo=call_fifo.path,
                feedback_fifo=feedback_fifo.path,
                scriptlet=scriptlet,
                env=self._env,
            )

            # FIXME: refactor ctl protocol server

            with tempfile.TemporaryFile(mode="w+") as script_file:
                print(script, file=script_file)
                script_file.flush()
                script_file.seek(0)
                process = subprocess.Popen(  # pylint: disable=consider-using-with
                    ["/bin/sh"], stdin=script_file, cwd=work_dir
                )

            status = None
            try:
                while status is None:
                    function_call = call_fifo.read()
                    if function_call:
                        # Handle the function and let caller know that function
                        # call has been handled (must contain at least a
                        # newline, anything beyond is considered an error by
                        # snapcraftctl)
                        self._handle_control_api(scriptlet_name, function_call.strip())
                        feedback_fifo.write("\n")

                    status = process.poll()

                    # Don't loop TOO busily
                    time.sleep(0.1)
            except Exception as error:
                feedback_fifo.write(f"{error!s}\n")
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

    def _handle_control_api(self, scriptlet_name, function_call) -> None:
        """Parse the message from the client and invoke the appropriate action."""
        try:
            function_json = json.loads(function_call)
        except json.decoder.JSONDecodeError as err:
            raise RuntimeError(
                "{!r} scriptlet called a function with invalid json: "
                "{}".format(scriptlet_name, function_call)
            ) from err

        for attr in ["function", "args"]:
            if attr not in function_json:
                raise RuntimeError(
                    f"{scriptlet_name!r} control call missing attribute {attr!r}"
                )

        function_name = function_json["function"]

        if function_name == "pull":
            self._builtin_pull()
        elif function_name == "build":
            self._builtin_build()
        elif function_name == "stage":
            self._builtin_stage()
        elif function_name == "prime":
            self._builtin_prime()
        else:
            raise errors.InvalidControlAPICall(
                part_name=self._part.name,
                scriptlet_name=scriptlet_name,
                message=f"invalid function {function_name!r}",
            )


def _migrate_files(
    *,
    files: Set[str],
    dirs: Set[str],
    srcdir: str,
    destdir: str,
    missing_ok: bool = False,
    follow_symlinks: bool = False,
    fixup_func=lambda *args: None,
):
    for dirname in sorted(dirs):
        src = os.path.join(srcdir, dirname)
        dst = os.path.join(destdir, dirname)

        file_utils.create_similar_directory(src, dst)

    for filename in sorted(files):
        src = os.path.join(srcdir, filename)
        dst = os.path.join(destdir, filename)

        if missing_ok and not os.path.exists(src):
            continue

        # If the file is already here and it's a symlink, leave it alone.
        if os.path.islink(dst):
            continue

        # Otherwise, remove and re-link it.
        if os.path.exists(dst):
            os.remove(dst)

        file_utils.link_or_copy(src, dst, follow_symlinks=follow_symlinks)

        fixup_func(dst)


def _check_conflicts(
    part_name: str, srcdir: str, destdir: str, files: List[str]
) -> None:
    conflict_files: List[str] = []

    for filename in files:
        src = os.path.join(srcdir, filename)
        dst = os.path.join(destdir, filename)

        if collisions.paths_collide(src, dst):
            conflict_files.append(filename)

    if conflict_files:
        raise errors.StageFilesConflict(
            part_name=part_name, conflicting_files=conflict_files
        )


def _fix_pkg_config(
    root: Union[str, Path],
    pkg_config_file: Union[str, Path],
    prefix_trim: Optional[Union[str, Path]] = None,
) -> None:
    """Rewrite the prefix entry in a pkg-config file.

    :param root: The root to add to the configuration prefix.
    :param pkg_config_file: The pkg-config file to process.
    :param prefix_trim: The initial path to remove from the configuration prefix.
    """
    # FIXME: see https://bugs.launchpad.net/snapcraft/+bug/1916281
    pattern_trim = None
    if prefix_trim:
        pattern_trim = re.compile("^prefix={}(?P<prefix>.*)".format(prefix_trim))
    pattern = re.compile("^prefix=(?P<prefix>.*)")

    with fileinput.input(pkg_config_file, inplace=True) as input_file:
        match_trim = None
        for line in input_file:
            match = pattern.search(str(line))
            if prefix_trim is not None and pattern_trim is not None:
                match_trim = pattern_trim.search(str(line))
            if prefix_trim is not None and match_trim is not None:
                print("prefix={}{}".format(root, match_trim.group("prefix")))
            elif match:
                print("prefix={}{}".format(root, match.group("prefix")))
            else:
                print(line, end="")
