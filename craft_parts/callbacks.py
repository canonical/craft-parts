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

"""Register and execute callback functions."""

import itertools
import logging
from pathlib import Path
from typing import Callable, Iterable, List, NamedTuple, Optional, Set, Union

from craft_parts import errors
from craft_parts.infos import ProjectInfo, StepInfo
from craft_parts.steps import Step


class CallbackHook(NamedTuple):
    """A callback hook."""

    function: Callable
    step_list: Optional[List[Step]]


FilterCallback = Callable[[ProjectInfo], Iterable[str]]
ExecutionCallback = Callable[[ProjectInfo], None]
StepCallback = Callable[[StepInfo], bool]
ConfigureOverlayCallback = Callable[[Path, ProjectInfo], None]
Callback = Union[
    FilterCallback, ExecutionCallback, StepCallback, ConfigureOverlayCallback
]

_STAGE_PACKAGE_FILTERS: List[CallbackHook] = []
_OVERLAY_HOOKS: List[CallbackHook] = []
_PROLOGUE_HOOKS: List[CallbackHook] = []
_EPILOGUE_HOOKS: List[CallbackHook] = []
_PRE_STEP_HOOKS: List[CallbackHook] = []
_POST_STEP_HOOKS: List[CallbackHook] = []

logger = logging.getLogger(__name__)


def register_stage_packages_filter(func: FilterCallback) -> None:
    """Register a callback function for stage packages dependency cutoff.

    Craft Parts includes mechanisms to filter out stage package dependencies
    in snap bases. This is now deprecated, and a function providing an explicit
    list of exclusions should be provided by the application.

    :param func: The callback function returning the filtered packages iterator.
    """
    _ensure_not_defined(func, _STAGE_PACKAGE_FILTERS)
    _STAGE_PACKAGE_FILTERS.append(CallbackHook(func, None))


def register_configure_overlay(func: ConfigureOverlayCallback) -> None:
    """Register a callback function to configure the mounted overlay.

    This "hook" is called after the overlay's package cache layer is mounted, but
    *before* the package list is refreshed. It can be used to configure the
    overlay's system, typically to install extra package repositories for Apt.
    Note that when the hook is called the overlay is mounted but *not* chrooted
    into.

    :param func: The callback function that will be called with the location of
      the overlay mount and the project info.
    """
    _ensure_not_defined(func, _OVERLAY_HOOKS)
    _OVERLAY_HOOKS.append(CallbackHook(func, None))


def register_prologue(func: ExecutionCallback) -> None:
    """Register an execution prologue callback function.

    :param func: The callback function to run.
    """
    _ensure_not_defined(func, _PROLOGUE_HOOKS)
    _PROLOGUE_HOOKS.append(CallbackHook(func, None))


def register_epilogue(func: ExecutionCallback) -> None:
    """Register an execution epilogue callback function.

    :param func: The callback function to run.
    """
    _ensure_not_defined(func, _EPILOGUE_HOOKS)
    _EPILOGUE_HOOKS.append(CallbackHook(func, None))


def register_pre_step(
    func: StepCallback, *, step_list: Optional[List[Step]] = None
) -> None:
    """Register a pre-step callback function.

    :param func: The callback function to run.
    :param step_list: The steps before which the callback function should run.
        If not specified, the callback function will be executed before all steps.
    """
    _ensure_not_defined(func, _PRE_STEP_HOOKS)
    _PRE_STEP_HOOKS.append(CallbackHook(func, step_list))


def register_post_step(
    func: StepCallback, *, step_list: Optional[List[Step]] = None
) -> None:
    """Register a post-step callback function.

    :param func: The callback function to run.
    :param step_list: The steps after which the callback function should run.
        If not specified, the callback function will be executed after all steps.
    """
    _ensure_not_defined(func, _POST_STEP_HOOKS)
    _POST_STEP_HOOKS.append(CallbackHook(func, step_list))


def unregister_all() -> None:
    """Clear all existing registered callback functions."""
    _STAGE_PACKAGE_FILTERS[:] = []
    _OVERLAY_HOOKS[:] = []
    _PROLOGUE_HOOKS[:] = []
    _EPILOGUE_HOOKS[:] = []
    _PRE_STEP_HOOKS[:] = []
    _POST_STEP_HOOKS[:] = []


def get_stage_packages_filters(project_info: ProjectInfo) -> Optional[Set[str]]:
    """Obtain the list of stage packages to be filtered out.

    :param project_info: The project information to be sent to callback functions.

    :return: An iterator for the list of packages to be filtered out.
    """
    if not _STAGE_PACKAGE_FILTERS:
        return None

    return set(
        itertools.chain(*[f.function(project_info) for f in _STAGE_PACKAGE_FILTERS])
    )


def run_configure_overlay(overlay_dir: Path, project_info: ProjectInfo) -> None:
    """Run all registered 'configure overlay' callbacks.

    :param overlay_dir: The location where the overlay is mounted.
    :param project_info: The project information to be sent to callback functions.
    """
    for hook in _OVERLAY_HOOKS:
        hook.function(overlay_dir, project_info)


def run_prologue(project_info: ProjectInfo) -> None:
    """Run all registered execution prologue callbacks.

    :param project_info: The project information to be sent to callback functions.
    """
    for hook in _PROLOGUE_HOOKS:
        hook.function(project_info)


def run_epilogue(project_info: ProjectInfo) -> None:
    """Run all registered execution epilogue callbacks.

    :param project_info: The project information to be sent to callback functions.
    """
    for hook in _EPILOGUE_HOOKS:
        hook.function(project_info)


def run_pre_step(step_info: StepInfo) -> None:
    """Run all registered pre-step callback functions.

    :param step_info: the step information to be sent to the callback functions.
    """
    return _run_step(hook_list=_PRE_STEP_HOOKS, step_info=step_info)


def run_post_step(step_info: StepInfo) -> None:
    """Run all registered post-step callback functions.

    :param step_info: the step information to be sent to the callback functions.
    """
    return _run_step(hook_list=_POST_STEP_HOOKS, step_info=step_info)


def _run_step(*, hook_list: List[CallbackHook], step_info: StepInfo) -> None:
    for hook in hook_list:
        if not hook.step_list or step_info.step in hook.step_list:
            hook.function(step_info)


def _ensure_not_defined(func: Callback, hook_list: List[CallbackHook]) -> None:
    for hook in hook_list:
        if func == hook.function:
            raise errors.CallbackRegistrationError(
                f"callback function {hook.function.__name__!r} "
                f"is already registered."
            )
