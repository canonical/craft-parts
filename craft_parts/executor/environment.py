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
from typing import Any, Dict, Iterable, List, Optional, Union, cast

from craft_parts.infos import ProjectInfo, StepInfo
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
    parts_environment = _basic_environment_for_part(part=part, step_info=step_info)

    # Plugin's say.
    if step_info.step == Step.BUILD:
        plugin_environment = plugin.get_build_environment()
    else:
        plugin_environment = {}

    # Part's (user) say.
    user_environment = part.spec.build_environment or []

    # Create the script.
    with io.StringIO() as run_environment:
        print("#!/bin/bash", file=run_environment)
        print("set -euo pipefail", file=run_environment)

        print("# Environment", file=run_environment)

        print("## Application environment", file=run_environment)
        for key, val in step_info.global_environment.items():
            print(f'export {key}="{val}"', file=run_environment)
        for key, val in step_info.step_environment.items():
            print(f'export {key}="{val}"', file=run_environment)

        print("## Part environment", file=run_environment)
        for key, val in parts_environment.items():
            print(f'export {key}="{val}"', file=run_environment)

        print("## Plugin environment", file=run_environment)
        for key, val in plugin_environment.items():
            print(f'export {key}="{val}"', file=run_environment)

        print("## User environment", file=run_environment)
        for env in user_environment:
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
    part_environment = _get_step_environment(step_info)
    paths = [part.part_install_dir, part.stage_dir]

    bin_paths = []
    for path in paths:
        bin_paths.extend(os_utils.get_bin_paths(root=path, existing_only=True))

    if bin_paths:
        bin_paths.append("$PATH")
        part_environment["PATH"] = _combine_paths(
            paths=bin_paths, prepend="", separator=":"
        )

    include_paths = []
    for path in paths:
        include_paths.extend(
            os_utils.get_include_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if include_paths:
        for envvar in ["CPPFLAGS", "CFLAGS", "CXXFLAGS"]:
            part_environment[envvar] = _combine_paths(
                paths=include_paths, prepend="-isystem ", separator=" "
            )

    library_paths = []
    for path in paths:
        library_paths.extend(
            os_utils.get_library_paths(root=path, arch_triplet=step_info.arch_triplet)
        )

    if library_paths:
        part_environment["LDFLAGS"] = _combine_paths(
            paths=library_paths, prepend="-L", separator=" "
        )

    pkg_config_paths = []
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


def _get_global_environment(info: ProjectInfo) -> Dict[str, str]:
    """Add project and part information variables to the environment.

    :param step_info: Information about the current step.

    :return: A dictionary containing environment variables and values.
    """
    global_environment = {
        "CRAFT_ARCH_TRIPLET": info.arch_triplet,
        "CRAFT_TARGET_ARCH": info.target_arch,
        "CRAFT_PARALLEL_BUILD_COUNT": str(info.parallel_build_count),
        "CRAFT_PROJECT_DIR": str(info.project_dir),
        "CRAFT_OVERLAY": str(info.overlay_mount_dir),
        "CRAFT_STAGE": str(info.stage_dir),
        "CRAFT_PRIME": str(info.prime_dir),
    }
    if info.project_name is not None:
        global_environment["CRAFT_PROJECT_NAME"] = str(info.project_name)

    return global_environment


def _get_step_environment(step_info: StepInfo) -> Dict[str, str]:
    """Add project and part information variables to the environment.

    :param step_info: Information about the current step.

    :return: A dictionary containing environment variables and values.
    """
    global_environment = _get_global_environment(step_info.project_info)

    step_environment = {
        **global_environment,
        "CRAFT_PART_NAME": step_info.part_name,
        "CRAFT_STEP_NAME": getattr(step_info.step, "name", ""),
        "CRAFT_PART_SRC": str(step_info.part_src_dir),
        "CRAFT_PART_SRC_WORK": str(step_info.part_src_subdir),
        "CRAFT_PART_BUILD": str(step_info.part_build_dir),
        "CRAFT_PART_BUILD_WORK": str(step_info.part_build_subdir),
        "CRAFT_PART_INSTALL": str(step_info.part_install_dir),
    }
    return step_environment


def _combine_paths(paths: Iterable[str], prepend: str, separator: str) -> str:
    """Combine list of paths into a string.

    :param paths: The list of paths to stringify.
    :param prepend: A prefix to prepend to each path in the string.
    :param separator: A string to place between each path in the string.

    :return: A string with the combined paths.
    """
    paths = [f"{prepend}{p}" for p in paths]
    return separator.join(paths)


def expand_environment(
    data: Dict[str, Any], *, info: ProjectInfo, skip: Optional[List[str]] = None
) -> None:
    """Replace global variables with their values.

    Global variables are defined by craft-parts and are the subset of the
    ``CRAFT_*`` step execution environment variables that don't depend
    on the part or step being executed. The list of global variables include
    ``CRAFT_ARCH_TRIPLET``, ``CRAFT_PROJECT_DIR``, ``CRAFT_STAGE`` and
    ``CRAFT_PRIME``. Additional global variables can be defined by the
    application using craft-parts.

    :param data: A dictionary whose values will have variable names expanded.
    :param info: The project information.
    :param skip: Keys to skip when performing expansion.
    """
    global_environment = _get_global_environment(info)
    global_environment.update(info.global_environment)

    replacements: Dict[str, str] = {}
    for key, value in global_environment.items():
        # Support both $VAR and ${VAR} syntax
        replacements[f"${key}"] = value
        replacements[f"${{{key}}}"] = value

    for key in data:
        if not skip or key not in skip:
            data[key] = _replace_attr(data[key], replacements)


def _replace_attr(
    attr: Union[List[str], Dict[str, str], str], replacements: Dict[str, str]
) -> Union[List[str], Dict[str, str], str]:
    """Replace environment variables according to the replacements map."""
    if isinstance(attr, str):
        for replacement, value in replacements.items():
            attr = attr.replace(replacement, str(value))
        return attr

    if isinstance(attr, (list, tuple)):
        return [cast(str, _replace_attr(i, replacements)) for i in attr]

    if isinstance(attr, dict):
        result: Dict[str, str] = {}
        for key, value in attr.items():
            # Run replacements on both the key and value
            key = cast(str, _replace_attr(key, replacements))
            value = cast(str, _replace_attr(value, replacements))
            result[key] = value
        return result

    return attr
