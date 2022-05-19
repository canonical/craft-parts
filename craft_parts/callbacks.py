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

import logging
from collections import namedtuple
from typing import Callable, List, Optional, Union

from craft_parts import errors
from craft_parts.infos import ProjectInfo, StepInfo
from craft_parts.steps import Step

CallbackHook = namedtuple("CallbackHook", ["function", "step_list"])

ExecutionCallback = Callable[[ProjectInfo], None]
StepCallback = Callable[[StepInfo], bool]
Callback = Union[ExecutionCallback, StepCallback]

_PROLOGUE_HOOKS: List[CallbackHook] = []
_EPILOGUE_HOOKS: List[CallbackHook] = []
_PRE_STEP_HOOKS: List[CallbackHook] = []
_POST_STEP_HOOKS: List[CallbackHook] = []

logger = logging.getLogger(__name__)


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
    global _PROLOGUE_HOOKS, _EPILOGUE_HOOKS  # pylint: disable=global-statement
    global _PRE_STEP_HOOKS, _POST_STEP_HOOKS  # pylint: disable=global-statement
    _PROLOGUE_HOOKS = []
    _EPILOGUE_HOOKS = []
    _PRE_STEP_HOOKS = []
    _POST_STEP_HOOKS = []


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


def _run_step(*, hook_list: List[CallbackHook], step_info: StepInfo):
    for hook in hook_list:
        if not hook.step_list or step_info.step in hook.step_list:
            hook.function(step_info)


def _ensure_not_defined(func: Callback, hook_list: List[CallbackHook]):
    for hook in hook_list:
        if func == hook.function:
            raise errors.CallbackRegistrationError(
                f"callback function {hook.function.__name__!r} "
                f"is already registered."
            )
