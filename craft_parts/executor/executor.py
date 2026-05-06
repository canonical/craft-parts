# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

"""Definitions and helpers for the action executor."""

import logging
import shutil
import subprocess
from pathlib import Path

import distro
from typing_extensions import Self

from craft_parts import callbacks, overlays, packages, parts, plugins
from craft_parts.actions import Action, ActionType
from craft_parts.infos import PartInfo, ProjectInfo, StepInfo
from craft_parts.overlays import LayerHash, OverlayManager
from craft_parts.parts import Part, sort_parts
from craft_parts.steps import Step
from craft_parts.utils import os_utils

from .collisions import check_for_stage_collisions
from .environment import generate_step_environment
from .part_handler import PartHandler
from .step_handler import Stream

logger = logging.getLogger(__name__)


# Map each architecture to its Ubuntu archive URL.
_ARCH_ARCHIVE_URL = {
    "amd64": "http://archive.ubuntu.com/ubuntu",
    "i386": "http://archive.ubuntu.com/ubuntu",
    "arm64": "http://ports.ubuntu.com/ubuntu-ports",
    "armhf": "http://ports.ubuntu.com/ubuntu-ports",
    "ppc64el": "http://ports.ubuntu.com/ubuntu-ports",
    "riscv64": "http://ports.ubuntu.com/ubuntu-ports",
    "s390x": "http://ports.ubuntu.com/ubuntu-ports",
}


class Executor:
    """Execute lifecycle actions.

    The executor takes the part definition and a list of actions to run for
    a part and step. Action execution is stateless: no information is kept from
    the execution of previous parts. On-disk state information written after
    running each action is read by the sequencer before planning a new set of
    actions.

    :param part_list: The list of parts to process.
    :param project_info: Information about this project.
    :param track_stage_packages: Add primed stage packages to the prime state.
    :param extra_build_packages: Additional packages to install on the host system.
    :param extra_build_snaps: Additional snaps to install on the host system.
    :param ignore_patterns: File patterns to ignore when pulling local sources.
    :param use_host_sources: Whether overlay steps should also include the repository
      sources defined on the host.
    :param native_cross_builds: Whether to use native cross-compilation support.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        part_list: list[Part],
        project_info: ProjectInfo,
        extra_build_packages: list[str] | None = None,
        extra_build_snaps: list[str] | None = None,
        track_stage_packages: bool = False,
        ignore_patterns: list[str] | None = None,
        base_layer_dir: Path | None = None,
        base_layer_hash: LayerHash | None = None,
        use_host_sources: bool = False,
        native_cross_builds: bool = False,
    ) -> None:
        self._part_list = sort_parts(part_list)
        self._project_info = project_info
        self._extra_build_packages = extra_build_packages
        self._extra_build_snaps = extra_build_snaps
        self._track_stage_packages = track_stage_packages
        self._base_layer_hash = base_layer_hash
        self._handler: dict[str, PartHandler] = {}
        self._ignore_patterns = ignore_patterns
        self._use_host_sources = use_host_sources
        self._native_cross_builds = native_cross_builds

        # The cache layer level is set to the first part that doesn't organize
        # to the overlay coming after a part that organizes to the overlay.
        cache_level = 0
        organized_to_overlay = False

        for level, part in enumerate(self._part_list):
            if part.organizes_to_overlay:
                organized_to_overlay = True
            elif organized_to_overlay:
                cache_level = level
                break

        self._overlay_manager = OverlayManager(
            project_info=self._project_info,
            part_list=self._part_list,
            base_layer_dir=base_layer_dir,
            cache_level=cache_level,
            use_host_sources=use_host_sources,
        )

    def prologue(self) -> None:
        """Prepare the execution environment.

        This method is called before executing lifecycle actions.
        """
        if self._native_cross_builds:
            self._enable_cross_build_architecture()
        self._install_build_packages()
        self._install_build_snaps()

        self._verify_plugin_environment()

        # Update the overlay environment package list to allow installation of
        # overlay packages if the cache level is the first layer after the base,
        # to keep compatibility with existing behavior.
        if (
            any(p.spec.overlay_packages for p in self._part_list)
            and self._overlay_manager.cache_level == 0
        ):
            logger.info("Updating base overlay system")
            with overlays.PackageCacheMount(self._overlay_manager) as ctx:
                callbacks.run_configure_overlay(
                    self._project_info.overlay_mount_dir, self._project_info
                )
                ctx.refresh_packages_list()

        callbacks.run_prologue(self._project_info)

        # obtain the stage package exclusion set.
        packages.Repository.stage_packages_filters = (
            callbacks.get_stage_packages_filters(self._project_info)
        )

    def epilogue(self) -> None:
        """Finish and clean the execution environment.

        This method is called after executing lifecycle actions.
        """
        self._project_info.execution_finished = True
        callbacks.run_epilogue(self._project_info)

    def execute(
        self,
        actions: Action | list[Action],
        *,
        stdout: Stream = None,
        stderr: Stream = None,
    ) -> None:
        """Execute the specified action or list of actions.

        :param actions: An :class:`Action` object or list of :class:`Action`
           objects specifying steps to execute.

        :raises InvalidActionException: If the action parameters are invalid.
        """
        if isinstance(actions, Action):
            actions = [actions]

        for act in actions:
            self._run_action(act, stdout=stdout, stderr=stderr)

    def clean(self, initial_step: Step, *, part_names: list[str] | None = None) -> None:  # noqa: PLR0912
        """Clean the given parts, or all parts if none is specified.

        :param initial_step: The step to clean. More steps may be cleaned
            as a consequence of cleaning the initial step.
        :param part_names: A list with names of the parts to clean. If not
            specified, all parts will be cleaned and work directories
            will be removed.
        """
        selected_parts = parts.part_list_by_name(part_names, self._part_list)

        selected_steps = [initial_step, *initial_step.next_steps()]
        selected_steps.reverse()

        for part in selected_parts:
            handler = self._create_part_handler(part)

            for step in selected_steps:
                handler.clean_step(step=step)

        if not part_names:
            # also remove toplevel directories if part names are not specified
            for prime_dir in self._project_info.prime_dirs.values():
                if prime_dir.exists():
                    shutil.rmtree(prime_dir)
            # remove default partition alias symlink
            prime_alias_symlink = self._project_info.prime_alias_symlink
            if prime_alias_symlink:
                prime_alias_symlink.unlink(missing_ok=True)

            if initial_step <= Step.STAGE:
                for stage_dir in self._project_info.stage_dirs.values():
                    if stage_dir.exists():
                        shutil.rmtree(stage_dir)
                if self._project_info.backstage_dir.exists():
                    shutil.rmtree(self._project_info.backstage_dir)
                # remove default partition alias symlink
                stage_alias_symlink = self._project_info.stage_alias_symlink
                if stage_alias_symlink:
                    stage_alias_symlink.unlink(missing_ok=True)

            if initial_step <= Step.PULL:
                if self._project_info.parts_dir.exists():
                    shutil.rmtree(self._project_info.parts_dir)
                # remove default partition alias symlink
                parts_alias_symlink = self._project_info.parts_alias_symlink
                if parts_alias_symlink:
                    parts_alias_symlink.unlink(missing_ok=True)

            if (
                initial_step <= Step.BUILD
                and self._project_info.partition_dir
                and self._project_info.partition_dir.exists()
            ):
                shutil.rmtree(self._project_info.partition_dir)

            if initial_step <= Step.OVERLAY:
                for overlay in self._project_info.dirs.overlay_dirs.values():
                    if overlay.exists():
                        shutil.rmtree(overlay)

    def _run_action(
        self,
        action: Action,
        *,
        stdout: Stream,
        stderr: Stream,
    ) -> None:
        """Execute the given action for a part using the provided step information.

        :param action: The lifecycle action to run.
        """
        part = parts.part_by_name(action.part_name, self._part_list)

        logger.debug("execute action %s:%s", part.name, action)

        if action.action_type == ActionType.SKIP:
            logger.debug("Skip execution of %s (because %s)", action, action.reason)
            # update project variables if action is skipped
            if action.project_vars:
                self._project_info.project_vars.update_from(
                    action.project_vars, action.part_name
                )
            return

        if action.step == Step.STAGE:
            check_for_stage_collisions(
                part_list=self._part_list, partitions=self._project_info.partitions
            )

        handler = self._create_part_handler(part)
        handler.run_action(action, stdout=stdout, stderr=stderr)

    def _create_part_handler(
        self,
        part: Part,
    ) -> PartHandler:
        """Instantiate a part handler for a new part."""
        if part.name in self._handler:
            return self._handler[part.name]

        handler = PartHandler(
            part,
            part_info=PartInfo(self._project_info, part),
            part_list=self._part_list,
            track_stage_packages=self._track_stage_packages,
            overlay_manager=self._overlay_manager,
            ignore_patterns=self._ignore_patterns,
            base_layer_hash=self._base_layer_hash,
            native_cross_builds=self._native_cross_builds,
        )
        self._handler[part.name] = handler

        return handler

    def _enable_cross_build_architecture(self) -> None:
        """Enable the target architecture for cross-building.

        Adds the target architecture via dpkg and configures APT sources
        for the foreign architecture (handling the archive.ubuntu.com vs
        ports.ubuntu.com split).  Existing sources are pinned to the host
        architecture so APT doesn't try to fetch foreign-arch packages from
        archives that don't carry them.
        """
        host_arch = self._project_info.arch_build_on
        target_arch = self._project_info.arch_build_for

        if host_arch == target_arch:
            return

        logger.info(
            "Enabling cross-build architecture: %s (host: %s)", target_arch, host_arch
        )

        # Add the foreign architecture to dpkg
        subprocess.run(
            ["dpkg", "--add-architecture", target_arch],
            check=True,
        )

        # Pin existing sources to the host architecture so they don't try
        # to fetch packages for the foreign architecture (which would 404
        # on archive.ubuntu.com for ports architectures and vice versa).
        self._pin_existing_sources_to_host(host_arch)

        # Add APT sources for the target architecture.
        target_url = _ARCH_ARCHIVE_URL.get(target_arch, "")
        if target_url:
            self._add_cross_build_sources(target_arch, target_url)

        # Refresh package lists to include the new architecture.
        # Clear the lru_cache first so refresh actually runs.
        packages.Repository.refresh_packages_list.cache_clear()  # type: ignore[attr-defined]
        packages.Repository.refresh_packages_list()

    def _pin_existing_sources_to_host(self, host_arch: str) -> None:
        """Restrict existing APT sources to the host architecture only.

        Without this, adding a foreign architecture via dpkg causes APT to
        try fetching foreign-arch package lists from all configured sources,
        which fails with 404 when the archive doesn't carry that architecture
        (e.g. ports architectures on archive.ubuntu.com).

        For deb822 .sources files, we inject an ``Architectures:`` field.
        For traditional sources.list, we add ``[arch=<host>]`` markers.
        """
        sources_dir = Path("/etc/apt/sources.list.d")

        # Handle deb822 .sources files (24.04+)
        if sources_dir.is_dir():
            for sources_file in sources_dir.glob("*.sources"):
                # Don't modify our own cross-build sources
                if sources_file.name == "craft-parts-cross-build.sources":
                    continue
                content = sources_file.read_text()
                if "Architectures:" not in content:
                    # Add Architectures field to each stanza
                    new_content = self._add_arch_to_deb822(content, host_arch)
                    sources_file.write_text(new_content)
                    logger.debug(
                        "Pinned %s to architecture %s", sources_file, host_arch
                    )

        # Handle traditional sources.list
        sources_list = Path("/etc/apt/sources.list")
        if sources_list.is_file():
            content = sources_list.read_text()
            if content.strip() and "[arch=" not in content:
                new_lines = []
                for line in content.splitlines(keepends=True):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        # Insert [arch=<host>] after "deb " or "deb-src "
                        for prefix in ("deb-src ", "deb "):
                            if stripped.startswith(prefix):
                                pinned_line = line.replace(
                                    prefix, f"{prefix}[arch={host_arch}] ", 1
                                )
                                line = pinned_line  # noqa: PLW2901
                                break
                    new_lines.append(line)
                sources_list.write_text("".join(new_lines))
                logger.debug("Pinned %s to architecture %s", sources_list, host_arch)

    @staticmethod
    def _add_arch_to_deb822(content: str, arch: str) -> str:
        """Add ``Architectures: <arch>`` to each stanza in a deb822 sources file."""
        result_lines: list[str] = []
        for line in content.splitlines(keepends=True):
            result_lines.append(line)
            # Insert Architectures after the Types line in each stanza
            if line.strip().startswith("Types:"):
                result_lines.append(f"Architectures: {arch}\n")
        return "".join(result_lines)

    def _add_cross_build_sources(self, target_arch: str, archive_url: str) -> None:
        """Add APT sources for the target architecture.

        :param target_arch: The target architecture (e.g. "arm64").
        :param archive_url: The archive URL for the target architecture.
        """
        sources_dir = Path("/etc/apt/sources.list.d")
        sources_dir.mkdir(parents=True, exist_ok=True)

        codename = distro.codename()
        if not codename:
            raise RuntimeError(
                "Cannot determine distribution codename; "
                "unable to configure cross-build APT sources."
            )

        suites = f"{codename} {codename}-updates {codename}-security"

        sources_content = (
            f"Types: deb\n"
            f"URIs: {archive_url}\n"
            f"Suites: {suites}\n"
            f"Components: main universe\n"
            f"Architectures: {target_arch}\n"
        )

        sources_file = sources_dir / "craft-parts-cross-build.sources"
        sources_file.write_text(sources_content)
        logger.debug(
            "Added %s sources for %s at %s", archive_url, target_arch, sources_file
        )

    def _install_build_packages(self) -> None:
        for part in self._part_list:
            self._create_part_handler(part)

        build_packages: set[str] = set(self._extra_build_packages or ())
        for handler in self._handler.values():
            build_packages.update(handler.build_packages)

        logger.info("Installing build-packages")
        packages.Repository.install_packages(sorted(build_packages))

    def _install_build_snaps(self) -> None:
        build_snaps: set[str] = set(self._extra_build_snaps or ())
        for handler in self._handler.values():
            build_snaps.update(handler.build_snaps)

        if not build_snaps:
            return

        if os_utils.is_inside_container():
            logger.warning(
                "The following snaps are required but not installed as the "
                "application is running inside docker or podman container: %s.\n"
                "Please ensure the environment is properly setup before "
                "continuing.\nIgnore this message if the appropriate measures "
                "have already been taken.",
                ", ".join(build_snaps),
            )
        else:
            logger.info("Installing build-snaps")
            packages.snaps.install_snaps(build_snaps)

    def _verify_plugin_environment(self) -> None:
        for part in self._part_list:
            logger.debug("verify plugin environment for part %r", part.name)

            part_info = PartInfo(self._project_info, part)
            plugin_class = plugins.get_plugin_class(part.plugin_name)
            plugin = plugin_class(
                properties=part.plugin_properties,
                part_info=part_info,
            )
            env = generate_step_environment(
                part=part,
                plugin=plugin,
                step_info=StepInfo(part_info, Step.BUILD),
            )
            validator = plugin_class.validator_class(
                part_name=part.name, env=env, properties=part.plugin_properties
            )
            validator.validate_environment(part_dependencies=part.dependencies)


class ExecutionContext:
    """A context manager to handle lifecycle action executions."""

    def __init__(
        self,
        *,
        executor: Executor,
    ) -> None:
        self._executor = executor

    def __enter__(self) -> Self:
        self._executor.prologue()
        return self

    def __exit__(self, *exc: object) -> None:
        self._executor.epilogue()

    def execute(
        self,
        actions: Action | list[Action],
        *,
        stdout: Stream = None,
        stderr: Stream = None,
    ) -> None:
        """Execute the specified action or list of actions.

        :param actions: An :class:`Action` object or list of :class:`Action`
           objects specifying steps to execute.

        :raises InvalidActionException: If the action parameters are invalid.
        """
        self._executor.execute(actions, stdout=stdout, stderr=stderr)
