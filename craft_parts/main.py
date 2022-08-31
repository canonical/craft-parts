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

"""Part crafting command line tool.

This is the main entry point for the craft_parts package, invoked
when running `python -mcraft_parts`. It provides basic functionality
to process a parts specification and display the planned sequence
of actions (using `--dry-run`) or execute them.
"""

import argparse
import logging
import subprocess
import sys
from functools import partial
from pathlib import Path

import yaml
from xdg import BaseDirectory  # type: ignore

import craft_parts
import craft_parts.errors
from craft_parts import ActionType, Step


def main():
    """Run the command-line interface."""
    options = _parse_arguments()

    if options.version:
        print(f"craft-parts {craft_parts.__version__}")
        sys.exit()

    if options.trace:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level)

    try:
        _process_parts(options)
    except OSError as err:
        msg = err.strerror
        if err.filename:
            msg = f"{err.filename}: {msg}"
        print(f"Error: {msg}.", file=sys.stderr)
        sys.exit(1)
    except craft_parts.errors.PartSpecificationError as err:
        print(f"Error: invalid parts specification: {err}", file=sys.stderr)
        sys.exit(2)
    except craft_parts.errors.PartsError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(3)
    except (ValueError, TypeError) as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(4)
    except RuntimeError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(5)


def _process_parts(options: argparse.Namespace) -> None:
    with open(options.file) as opt_file:
        part_data = yaml.safe_load(opt_file)

    cache_dir = options.cache_dir
    if not cache_dir:
        cache_dir = BaseDirectory.save_cache_path("craft-parts")

    if options.overlay_base:
        # The base layer hash algorithm is not specified and could be anything
        # that remains constant for a given base. The CLI tool just uses the path
        # to the base for simplicity, but applications can (and probably should)
        # use a real digest.
        base_layer_hash = options.overlay_base.encode()
        overlay_base = Path(options.overlay_base)
    else:
        base_layer_hash = b""
        overlay_base = None

    lcm = craft_parts.LifecycleManager(
        part_data,
        application_name=options.application_name,
        work_dir=options.work_dir,
        cache_dir=cache_dir,
        base=options.base,
        base_layer_dir=overlay_base,
        base_layer_hash=base_layer_hash,
    )

    command = options.command if options.command else "prime"
    if command == "clean":
        _do_clean(lcm, options)
        sys.exit()

    _do_step(lcm, options)


def _do_step(lcm: craft_parts.LifecycleManager, options: argparse.Namespace) -> None:
    target_step = _parse_step(options.command) if options.command else Step.PRIME
    part_names = vars(options).get("parts", [])

    if options.refresh:
        lcm.refresh_packages_list()

    actions = lcm.plan(target_step, part_names)

    output_stream = None if options.verbose else subprocess.DEVNULL

    if options.dry_run:
        printed = False
        for action in actions:
            if options.show_skipped or action.action_type != ActionType.SKIP:
                print(_action_message(action))
                printed = True
        if not printed:
            print("No actions to execute.")
        sys.exit()

    with lcm.action_executor() as ctx:
        for action in actions:
            if options.show_skipped or action.action_type != ActionType.SKIP:
                print(f"Execute: {_action_message(action)}")
                ctx.execute(action, stdout=output_stream, stderr=output_stream)


def _do_clean(lcm: craft_parts.LifecycleManager, options: argparse.Namespace) -> None:
    if options.dry_run:
        return

    if not options.parts:
        print("Clean all parts.")

    lcm.clean(Step.PULL, part_names=options.parts)


def _action_message(action: craft_parts.Action) -> str:
    msg = {
        Step.PULL: {
            ActionType.RUN: "Pull",
            ActionType.RERUN: "Repull",
            ActionType.SKIP: "Skip pull",
            ActionType.UPDATE: "Update sources for",
        },
        Step.OVERLAY: {
            ActionType.RUN: "Overlay",
            ActionType.RERUN: "Re-overlay",
            ActionType.SKIP: "Skip overlay",
            ActionType.REAPPLY: "Reapply overlay for",
            ActionType.UPDATE: "Update overlay for",
        },
        Step.BUILD: {
            ActionType.RUN: "Build",
            ActionType.RERUN: "Rebuild",
            ActionType.SKIP: "Skip build",
            ActionType.UPDATE: "Update build for",
        },
        Step.STAGE: {
            ActionType.RUN: "Stage",
            ActionType.RERUN: "Restage",
            ActionType.SKIP: "Skip stage",
        },
        Step.PRIME: {
            ActionType.RUN: "Prime",
            ActionType.RERUN: "Re-prime",
            ActionType.SKIP: "Skip prime",
        },
    }

    message = f"{msg[action.step][action.action_type]} {action.part_name}"

    if action.reason:
        message += f" ({action.reason})"

    return message


def _parse_step(name: str) -> Step:
    step_map = {
        "pull": Step.PULL,
        "overlay": Step.OVERLAY,
        "build": Step.BUILD,
        "stage": Step.STAGE,
        "prime": Step.PRIME,
    }

    return step_map.get(name, Step.PRIME)


def _parse_arguments() -> argparse.Namespace:
    prog = "python -m craft_parts"
    description = (
        "A command line interface for the craft_parts module to build "
        "parts-based projects."
    )

    parser = argparse.ArgumentParser(prog=prog, description=description, add_help=False)
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )
    parser.add_argument(
        "-f",
        "--file",
        metavar="filename",
        default="parts.yaml",
        help="The parts specification file. Default is 'parts.yaml'.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Update the stage packages list before procceeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions to be executed and exit.",
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Also display skipped actions.",
    )
    parser.add_argument(
        "--work-dir",
        metavar="dirname",
        default=".",
        help="Use the specified work directory. Defaults to current dir.",
    )
    parser.add_argument(
        "--application-name",
        metavar="name",
        default="craft_parts",
        help="Set the application name. Default is 'craft_parts'.",
    )
    parser.add_argument(
        "--overlay-base",
        metavar="dirname",
        help="The overlay base directory",
    )
    parser.add_argument(
        "--base",
        metavar="name",
        default="",
        help="Use the specified build base. Defaults to host system.",
    )
    parser.add_argument(
        "--cache-dir",
        metavar="dirname",
        default="",
        help="Set an alternate cache directory location.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show execution output",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable debug messages.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display the craft-parts version and exit.",
    )

    help_parser = argparse.ArgumentParser(add_help=False)
    help_parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")

    add_subparser = partial(
        subparsers.add_parser, add_help=False, parents=[help_parser]
    )

    pull_parser = add_subparser("pull", help="Retrieve artifacts defined for a part.")
    pull_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to pull. Default is all parts.",
    )

    overlay_parser = add_subparser("overlay", help="Process part overlay.")
    overlay_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to overlay. Default is all parts.",
    )

    build_parser = add_subparser("build", help="Build artifacts defined for a part.")
    build_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to build. Default is all parts.",
    )

    stage_parser = add_subparser("stage", help="Stage artifacts built by a part.")
    stage_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to stage. Default is all parts.",
    )

    prime_parser = add_subparser(
        "prime", help="Refine stage and prepare final payload."
    )
    prime_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to prime. Default is all parts.",
    )

    clean_parser = add_subparser("clean", help="Remove a part's assets and state.")
    clean_parser.add_argument(
        "parts",
        nargs="*",
        help="The list of parts to clean. Default is all parts.",
    )

    return parser.parse_args()
