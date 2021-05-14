# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
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

"""Helpers to handle part environment setting."""

import io
import logging
from typing import Dict, Iterable

from craft_parts.infos import StepInfo
from craft_parts.parts import Part
from craft_parts.plugins import Plugin
from craft_parts.steps import Step
from craft_parts.utils import os_utils

logger = logging.getLogger(__name__)


def generate_step_environment(
    *, part: Part, plugin: Plugin, step_info: StepInfo
) -> str:
    """Generate an environment to use during step execution.

    :param part: The part being processed.
    :param plugin: The plugin used to build this part.
    :param step_info: Information about the step to be executed.

    :return: The environment to use when executing the step.
    """
    # Craft parts' say.
    our_build_environment = _basic_environment_for_part(part=part, step_info=step_info)

    step = step_info.step

    # Plugin's say.
    if step == Step.BUILD:
        plugin_environment = plugin.get_build_environment()
    else:
        plugin_environment = dict()

    # Part's (user) say.
    user_build_environment = part.spec.build_environment
    if not user_build_environment:
        user_build_environment = []

    # Create the script.
    with io.StringIO() as run_environment:
        print("#!/bin/bash", file=run_environment)
        print("set -euo pipefail", file=run_environment)

        print("# Environment", file=run_environment)

        print("## Part Environment", file=run_environment)
        for key, val in our_build_environment.items():
            print(f'export {key}="{val}"', file=run_environment)

        print("## Plugin Environment", file=run_environment)
        for key, val in plugin_environment.items():
            print(f'export {key}="{val}"', file=run_environment)

        print("## User Environment", file=run_environment)
        for env in user_build_environment:
            for key, val in env.items():
                print(f'export {key}="{val}"', file=run_environment)

        # Return something suitable for Runner.
        return run_environment.getvalue()


def _basic_environment_for_part(part: Part, *, step_info: StepInfo) -> Dict[str, str]:
    """Return the built-in part environment.

    :param part: The part to get environment information from.
    :param step_info: Information for this step.

    :return: A dictionary containing the built-in environment.
    """
    part_environment: Dict[str, str] = _get_step_environment(step_info)
    paths = [part.part_install_dir, part.stage_dir]

    bin_paths = list()
    for path in paths:
        bin_paths.extend(os_utils.get_bin_paths(root=path, existing_only=True))

    if bin_paths:
        bin_paths.append("$PATH")
        part_environment["PATH"] = _combine_paths(
            paths=bin_paths, prepend="", separator=":"
        )

    include_paths = list()
    for path in paths:
        include_paths.extend(
            os_utils.get_include_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if include_paths:
        for envvar in ["CPPFLAGS", "CFLAGS", "CXXFLAGS"]:
            part_environment[envvar] = _combine_paths(
                paths=include_paths, prepend="-isystem ", separator=" "
            )

    library_paths = list()
    for path in paths:
        library_paths.extend(
            os_utils.get_library_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if library_paths:
        part_environment["LDFLAGS"] = _combine_paths(
            paths=library_paths, prepend="-L", separator=" "
        )

    pkg_config_paths = list()
    for path in paths:
        pkg_config_paths.extend(
            os_utils.get_pkg_config_paths(
                root=path, arch_triplet=step_info.arch_triplet
            )
        )

    if pkg_config_paths:
        part_environment["PKG_CONFIG_PATH"] = _combine_paths(
            pkg_config_paths, prepend="", separator=":"
        )

    return part_environment


def _get_step_environment(step_info: StepInfo) -> Dict[str, str]:
    """Add project and part information variables to the environment.

    Variable names are prefixed by the application name in uppercase.

    :param step_info: Information about the current step.

    :return: A dictionary containing environment variables and values.
    """
    prefix = step_info.application_name.upper()

    return {
        f"{prefix}_ARCH_TRIPLET": step_info.arch_triplet,
        f"{prefix}_TARGET_ARCH": step_info.target_arch,
        f"{prefix}_PARALLEL_BUILD_COUNT": str(step_info.parallel_build_count),
        f"{prefix}_PART_NAME": step_info.part_name,
        f"{prefix}_PART_SRC": str(step_info.part_src_dir),
        f"{prefix}_PART_BUILD": str(step_info.part_build_dir),
        f"{prefix}_PART_BUILD_WORK": str(step_info.part_build_subdir),
        f"{prefix}_PART_INSTALL": str(step_info.part_install_dir),
        f"{prefix}_OVERLAY": str(step_info.overlay_mount_dir),
        f"{prefix}_STAGE": str(step_info.stage_dir),
        f"{prefix}_PRIME": str(step_info.prime_dir),
    }


def _combine_paths(paths: Iterable[str], prepend: str, separator: str) -> str:
    """Combine list of paths into a string.

    :param paths: The list of paths to stringify.
    :param prepend: A prefix to prepend to each path in the string.
    :param separator: A string to place between each path in the string.

    :return: A string with the combined paths.
    """
    paths = ["{}{}".format(prepend, p) for p in paths]
    return separator.join(paths)
