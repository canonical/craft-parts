# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Definitions and helpers for part handlers."""

import logging
import os
import os.path
import shutil
from glob import iglob
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from craft_parts import callbacks, errors, packages, plugins, sources
from craft_parts.actions import Action, ActionType
from craft_parts.infos import PartInfo, StepInfo
from craft_parts.packages import errors as packages_errors
from craft_parts.parts import Part
from craft_parts.plugins import Plugin
from craft_parts.state_manager import states
from craft_parts.state_manager.states import StepState
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .organize import organize_files
from .step_handler import StepContents, StepHandler

logger = logging.getLogger(__name__)


class PartHandler:
    """Handle steps for a part using the appropriate plugins.

    :param part: The part being processed.
    :param part_info: Information about the part being processed.
    :param part_list: A list containing all parts.
    """

    def __init__(
        self,
        part: Part,
        *,
        part_info: PartInfo,
        part_list: List[Part],
    ):
        self._part = part
        self._part_info = part_info
        self._part_list = part_list

        self._plugin = plugins.get_plugin(
            part=part,
            properties=part.plugin_properties,
            part_info=part_info,
        )

        self._part_properties = part.spec.marshal()
        self._source_handler = sources.get_source_handler(
            application_name=part_info.application_name,
            part=part,
            project_dirs=part_info.dirs,
        )

        self._build_packages = _get_build_packages(part=self._part, plugin=self._plugin)
        self._build_snaps = _get_build_snaps(part=self._part, plugin=self._plugin)

    def run_action(self, action: Action) -> None:
        """Execute the given action for this part using a plugin.

        :param action: The action to execute.
        """
        step_info = StepInfo(self._part_info, action.step)

        if action.action_type == ActionType.UPDATE:
            # TODO: add update action handler
            return

        if action.action_type == ActionType.RERUN:
            # TODO: clean step
            pass

        handler: Callable[[StepInfo], StepState]

        if action.step == Step.PULL:
            handler = self._run_pull
        elif action.step == Step.BUILD:
            handler = self._run_build
        elif action.step == Step.STAGE:
            handler = self._run_stage
        elif action.step == Step.PRIME:
            handler = self._run_prime
        else:
            raise RuntimeError("cannot run action for invalid step {action.step!r}")

        callbacks.run_pre_step(step_info)
        state = handler(step_info)
        state_file = states.state_file_path(self._part, action.step)
        state.write(state_file)
        callbacks.run_post_step(step_info)

    def _run_pull(self, step_info: StepInfo) -> StepState:
        _remove(self._part.part_src_dir)
        self._make_dirs()

        fetched_packages = self._fetch_stage_packages(step_info=step_info)
        fetched_snaps = self._fetch_stage_snaps()

        self._run_step(
            step_info=step_info,
            scriptlet_name="override-pull",
            work_dir=self._part.part_src_dir,
        )

        state = states.PullState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            assets={
                "stage-packages": fetched_packages,
                "stage-snaps": fetched_snaps,
                "source-details": getattr(self._source_handler, "source_details", None),
            },
        )

        return state

    def _run_build(self, step_info: StepInfo, *, update=False) -> StepState:
        self._make_dirs()
        _remove(self._part.part_build_dir)
        self._unpack_stage_packages()
        self._unpack_stage_snaps()

        # Copy source from the part source dir to the part build dir
        shutil.copytree(
            self._part.part_src_dir, self._part.part_build_dir, symlinks=True
        )

        # Perform the build step
        self._run_step(
            step_info=step_info,
            scriptlet_name="override-build",
            work_dir=self._part.part_build_dir,
        )

        # Organize the installed files as requested. We do this in the build step for
        # two reasons:
        #
        #   1. So cleaning and re-running the stage step works even if `organize` is
        #      used
        #   2. So collision detection takes organization into account, i.e. we can use
        #      organization to get around file collisions between parts when staging.
        #
        # If `update` is true, we give the snapcraft CLI permission to overwrite files
        # that already exist. Typically we do NOT want this, so that parts don't
        # accidentally clobber e.g. files brought in from stage-packages, but in the
        # case of updating build, we want the part to have the ability to organize over
        # the files it organized last time around. We can be confident that this won't
        # overwrite anything else, because to do so would require changing the
        # `organize` keyword, which will make the build step dirty and require a clean
        # instead of an update.
        self._organize(overwrite=update)

        assets = {
            "build-packages": self._build_packages,
            "build-snaps": self._build_snaps,
        }
        assets.update(_get_machine_manifest())

        state = states.BuildState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            assets=assets,
        )
        return state

    def _run_stage(self, step_info: StepInfo) -> StepState:
        self._make_dirs()

        contents = self._run_step(
            step_info=step_info,
            scriptlet_name="override-stage",
            work_dir=self._part.stage_dir,
        )

        state = states.StageState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            files=contents.files,
            directories=contents.dirs,
        )
        return state

    def _run_prime(self, step_info: StepInfo) -> StepState:
        self._make_dirs()

        contents = self._run_step(
            step_info=step_info,
            scriptlet_name="override-prime",
            work_dir=self._part.prime_dir,
        )

        state = states.PrimeState(
            part_properties=self._part_properties,
            project_options=step_info.project_options,
            files=contents.files,
            directories=contents.dirs,
        )
        return state

    def _run_step(
        self, *, step_info: StepInfo, scriptlet_name: str, work_dir: Path
    ) -> StepContents:
        """Run the scriptlet if overriding, otherwise run the built-in handler.

        :param step_info: Information about the step to execute.
        :param scriptlet_name: The name of this step's scriptlet.
        :param work_dir: The path to run the scriptlet on.

        :return: If step is Stage or Prime, return a tuple of sets containing
            the step's file and directory artifacts.
        """
        if not step_info.step:
            raise RuntimeError("request to run an undefined step")

        step_handler = StepHandler(
            self._part,
            step_info=step_info,
            plugin=self._plugin,
            source_handler=self._source_handler,
        )
        scriptlet = self._part.spec.get_scriptlet(step_info.step)
        if scriptlet:
            step_handler.run_scriptlet(
                scriptlet, scriptlet_name=scriptlet_name, work_dir=work_dir
            )
            return StepContents()

        return step_handler.run_builtin()

    def _make_dirs(self):
        dirs = [
            self._part.part_src_dir,
            self._part.part_build_dir,
            self._part.part_install_dir,
            self._part.part_state_dir,
            self._part.part_run_dir,
            self._part.stage_dir,
            self._part.prime_dir,
        ]
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)

    def _organize(self, *, overwrite=False):
        mapping = self._part.spec.organize_files
        organize_files(
            part_name=self._part.name,
            mapping=mapping,
            base_dir=self._part.part_install_dir,
            overwrite=overwrite,
        )

    def _fetch_stage_packages(self, *, step_info: StepInfo) -> Optional[List[str]]:
        stage_packages = self._part.spec.stage_packages
        if not stage_packages:
            return None

        try:
            fetched_packages = packages.Repository.fetch_stage_packages(
                application_name=step_info.application_name,
                package_names=stage_packages,
                target_arch=step_info.target_arch,
                base=step_info.base,
                stage_packages_path=self._part.part_packages_dir,
            )
        except packages_errors.PackageNotFound as err:
            raise errors.StagePackageNotFound(
                part_name=self._part.name, package_name=err.package_name
            )

        return fetched_packages

    def _fetch_stage_snaps(self):
        stage_snaps = self._part.spec.stage_snaps
        if not stage_snaps:
            return None

        packages.snaps.download_snaps(
            snaps_list=stage_snaps, directory=str(self._part.part_snaps_dir)
        )

        return stage_snaps

    def _unpack_stage_packages(self):
        packages.Repository.unpack_stage_packages(
            stage_packages_path=self._part.part_packages_dir,
            install_path=Path(self._part.part_install_dir),
        )

    def _unpack_stage_snaps(self):
        stage_snaps = self._part.spec.stage_snaps
        if not stage_snaps:
            return

        snaps_dir = self._part.part_snaps_dir
        install_dir = self._part.part_install_dir

        logger.debug("Unpacking stage-snaps to %s", install_dir)

        snap_files = iglob(os.path.join(snaps_dir, "*.snap"))
        snap_sources = (
            sources.SnapSource(source=s, part_src_dir=snaps_dir) for s in snap_files
        )

        for snap_source in snap_sources:
            snap_source.provision(str(install_dir), clean_target=False, keep=True)


def _remove(filename: Path) -> None:
    if filename.is_symlink() or filename.is_file():
        logger.debug("remove file %s", filename)
        os.unlink(filename)
    elif filename.is_dir():
        logger.debug("remove directory %s", filename)
        shutil.rmtree(filename)


def _get_build_packages(*, part: Part, plugin: Plugin) -> List[str]:
    """Obtain the list of build packages from part, source, and plugin."""
    all_packages: List[str] = []

    build_packages = part.spec.build_packages
    if build_packages:
        logger.debug("part build packages: %s", build_packages)
        all_packages.extend(build_packages)

    source = part.spec.source
    if source:
        repo = packages.Repository
        source_type = sources.get_source_type_from_uri(source)
        source_build_packages = repo.get_packages_for_source_type(source_type)
        if source_build_packages:
            logger.debug("source build packages: %s", source_build_packages)
            all_packages.extend(source_build_packages)

    plugin_build_packages = plugin.get_build_packages()
    if plugin_build_packages:
        logger.debug("plugin build packages: %s", plugin_build_packages)
        all_packages.extend(plugin_build_packages)

    return all_packages


def _get_build_snaps(*, part: Part, plugin: Plugin) -> List[str]:
    """Obtain the list of build snaps from part and plugin."""
    all_snaps: List[str] = []

    build_snaps = part.spec.build_snaps
    if build_snaps:
        logger.debug("part build snaps: %s", build_snaps)
        all_snaps.extend(build_snaps)

    plugin_build_snaps = plugin.get_build_snaps()
    if plugin_build_snaps:
        logger.debug("plugin build snaps: %s", plugin_build_snaps)
        all_snaps.extend(plugin_build_snaps)

    return all_snaps


def _get_machine_manifest() -> Dict[str, Any]:
    """Obtain information about the system OS and runtime environment."""
    return {
        "uname": os_utils.get_system_info(),
        "installed-packages": sorted(packages.Repository.get_installed_packages()),
        "installed-snaps": sorted(packages.snaps.get_installed_snaps()),
    }
