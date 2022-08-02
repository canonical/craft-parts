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

"""Project, part and step information classes."""

import logging
import platform
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_yaml import YamlModel

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.parts import Part
from craft_parts.steps import Step

logger = logging.getLogger(__name__)


_var_name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ProjectVar(YamlModel):
    """Project variables that can be updated using craftctl."""

    value: str
    updated: bool = False


class ProjectInfo:
    """Project-level information containing project-specific fields.

    :param application_name: A unique identifier for the application using
        Craft Parts.
    :param project_name: name of the project being built.
    :param cache_dir: The path to store cached packages and files. If not
        specified, a directory under the application name entry in the XDG
        base directory will be used.
    :param arch: The architecture to build for. Defaults to the host system
        architecture.
    :param parallel_build_count: The maximum number of concurrent jobs to be
        used to build each part of this project.
    :param project_dirs: The project work directories.
    :param project_name: The name of the project.
    :param project_vars_part_name: Project variables can be set only if
        the part name matches this name.
    :param project_vars: A dictionary containing the project variables.
    :param custom_args: Any additional arguments defined by the application
        when creating a :class:`LifecycleManager`.
    """

    def __init__(
        self,
        *,
        application_name: str,
        cache_dir: Path,
        arch: str = "",
        base: str = "",
        parallel_build_count: int = 1,
        project_dirs: Optional[ProjectDirs] = None,
        project_name: Optional[str] = None,
        project_vars_part_name: Optional[str] = None,
        project_vars: Optional[Dict[str, str]] = None,
        **custom_args,  # custom passthrough args
    ):
        if not project_dirs:
            project_dirs = ProjectDirs()

        pvars = project_vars or {}

        self._application_name = application_name
        self._cache_dir = Path(cache_dir).expanduser().resolve()
        self._set_machine(arch)
        self._base = base  # TODO: infer base if not specified
        self._parallel_build_count = parallel_build_count
        self._dirs = project_dirs
        self._project_name = project_name
        self._project_vars_part_name = project_vars_part_name
        self._project_vars = {k: ProjectVar(value=v) for k, v in pvars.items()}
        self._custom_args = custom_args
        self.global_environment: Dict[str, str] = {}

        self.execution_finished = False

    def __getattr__(self, name):
        if hasattr(self._dirs, name):
            return getattr(self._dirs, name)

        if name in self._custom_args:
            return self._custom_args[name]

        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")

    @property
    def custom_args(self) -> List[str]:
        """Return the list of custom argument names."""
        return list(self._custom_args.keys())

    @property
    def application_name(self) -> str:
        """Return the name of the application using craft-parts."""
        return self._application_name

    @property
    def cache_dir(self) -> Path:
        """Return the directory used to store cached files."""
        return self._cache_dir

    @property
    def arch_triplet(self) -> str:
        """Return the machine-vendor-os platform triplet definition."""
        return self._machine["triplet"]

    @property
    def is_cross_compiling(self) -> bool:
        """Whether the target and host architectures are different."""
        return self._arch != self._host_arch

    @property
    def parallel_build_count(self) -> int:
        """Return the maximum allowable number of concurrent build jobs."""
        return self._parallel_build_count

    @property
    def host_arch(self) -> str:
        """Return the host architecture used for debs, snaps and charms."""
        return self._host_machine["deb"]

    @property
    def target_arch(self) -> str:
        """Return the target architecture used for debs, snaps and charms."""
        return self._machine["deb"]

    @property
    def base(self) -> str:
        """Return the project build base."""
        return self._base

    @property
    def dirs(self) -> ProjectDirs:
        """Return the project's work directories."""
        return self._dirs

    @property
    def project_name(self) -> Optional[str]:
        """Return the name of the project using craft-parts."""
        return self._project_name

    @property
    def project_options(self) -> Dict[str, Any]:
        """Obtain a project-wide options dictionary."""
        return {
            "application_name": self.application_name,
            "arch_triplet": self.arch_triplet,
            "target_arch": self.target_arch,
            "project_vars_part_name": self._project_vars_part_name,
            "project_vars": self._project_vars,
        }

    def set_project_var(
        self,
        name: str,
        value: str,
        raw_write: bool = False,
        *,
        part_name: Optional[str] = None,
    ) -> None:
        """Set the value of a project variable.

        Variable values can be set once. Project variables are not intended for
        logic construction in user scripts, setting it multiple times is likely to
        be an error.

        :param name: The project variable name.
        :param value: The new project variable value.
        :param part_name: If not None, variable setting is restricted to the named part.
        :param raw_write: Whether the variable is written without access verifications.

        :raise ValueError: If there is no custom argument with the given name.
        :raise RuntimeError: If a write-once variable is set a second time, or if a
            part name is specified and the variable is set from a different part.
        """
        self._ensure_valid_variable_name(name)

        if raw_write:
            self._project_vars[name].value = value
            self._project_vars[name].updated = True
            return

        if self._project_vars[name].updated:
            raise RuntimeError(f"variable {name!r} can be set only once")

        if self._project_vars_part_name == part_name:
            self._project_vars[name].value = value
            self._project_vars[name].updated = True
        elif not self._project_vars_part_name:
            raise RuntimeError(
                f"variable {name!r} can only be set in a part that "
                "adopts external metadata"
            )
        else:
            raise RuntimeError(
                f"variable {name!r} can only be set "
                f"in part {self._project_vars_part_name!r}"
            )

    def get_project_var(self, name: str, *, raw_read: bool = False) -> str:
        """Get the value of a project variable.

        Variables must be consumed by the application only after the lifecycle
        execution ends to prevent unexpected behavior if steps are skipped.

        :param name: The project variable name.
        :param raw_read: Whether the variable is read without access verifications.
        :return: The value of the variable.

        :raise ValueError: If there is no project variable with the given name.
        :raise RuntimeError: If the variable is consumed during the lifecycle execution.
        """
        self._ensure_valid_variable_name(name)
        if not raw_read and not self.execution_finished:
            raise RuntimeError(
                f"cannot consume variable {name!r} during lifecycle execution"
            )

        return self._project_vars[name].value

    def _ensure_valid_variable_name(self, name: str) -> None:
        """Raise an error if variable name is invalid.

        :param name: The variable name to verify.
        """
        if not _var_name_pattern.match(name):
            raise ValueError(f"{name!r} is not a valid variable name")

        if name not in self._project_vars:
            raise ValueError(f"{name!r} not in project variables")

    def _set_machine(self, arch: Optional[str]):
        """Initialize host and target machine information based on the architecture.

        :param arch: The architecture to use. If empty, assume the
            host system architecture.
        """
        # set host machine and arch
        self._host_arch = _get_host_architecture()
        host_machine = _ARCH_TRANSLATIONS.get(self._host_arch)
        if not host_machine:
            raise errors.InvalidArchitecture(self._host_arch)
        self._host_machine = host_machine

        # set target machine and arch
        if not arch:
            arch = self._host_arch
            logger.debug("Setting target machine to %s", arch)
        machine = _ARCH_TRANSLATIONS.get(arch)
        if not machine:
            raise errors.InvalidArchitecture(arch)

        self._arch = arch
        self._machine = machine


class PartInfo:
    """Part-level information containing project and part fields.

    :param project_info: The project information.
    :param part: The part we want to obtain information from.
    """

    def __init__(
        self,
        project_info: ProjectInfo,
        part: Part,
    ):
        self._project_info = project_info
        self._part_name = part.name
        self._part_src_dir = part.part_src_dir
        self._part_src_subdir = part.part_src_subdir
        self._part_build_dir = part.part_build_dir
        self._part_build_subdir = part.part_build_subdir
        self._part_install_dir = part.part_install_dir
        self._part_state_dir = part.part_state_dir

    def __getattr__(self, name):
        # Use composition and attribute cascading to avoid setting attributes
        # cumulatively in the init method.
        if hasattr(self._project_info, name):
            return getattr(self._project_info, name)

        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")

    @property
    def project_info(self) -> ProjectInfo:
        """Return the project information."""
        return self._project_info

    @property
    def part_name(self) -> str:
        """Return the name of the part we're providing information about."""
        return self._part_name

    @property
    def part_src_dir(self) -> Path:
        """Return the subdirectory containing the part's source code."""
        return self._part_src_dir

    @property
    def part_src_subdir(self) -> Path:
        """Return the subdirectory in source containing the source subtree (if any)."""
        return self._part_src_subdir

    @property
    def part_build_dir(self) -> Path:
        """Return the subdirectory containing the part's build tree."""
        return self._part_build_dir

    @property
    def part_build_subdir(self) -> Path:
        """Return the subdirectory in build containing the source subtree (if any)."""
        return self._part_build_subdir

    @property
    def part_install_dir(self) -> Path:
        """Return the subdirectory to install the part's build artifacts."""
        return self._part_install_dir

    @property
    def part_state_dir(self) -> Path:
        """Return the subdirectory containing this part's lifecycle state."""
        return self._part_state_dir

    def set_project_var(
        self, name: str, value: str, *, raw_write: bool = False
    ) -> None:
        """Set the value of a project variable.

        Variable values can be set once. Project variables are not intended for
        logic construction in user scripts, setting it multiple times is likely to
        be an error.

        :param name: The project variable name.
        :param value: The new project variable value.
        :param raw_write: Whether the variable is written without access verifications.

        :raise ValueError: If there is no custom argument with the given name.
        :raise RuntimeError: If a write-once variable is set a second time, or if a
            part name is specified and the variable is set from a different part.
        """
        self._project_info.set_project_var(
            name, value, part_name=self._part_name, raw_write=raw_write
        )

    def get_project_var(self, name: str, *, raw_read: bool = False) -> str:
        """Get the value of a project variable.

        Variables must be consumed by the application only after the lifecycle
        execution ends to prevent unexpected behavior if steps are skipped.

        :param name: The project variable name.
        :param raw_read: Whether the variable is read without access verifications.
        :return: The value of the variable.

        :raise ValueError: If there is no project variable with the given name.
        :raise RuntimeError: If the variable is consumed during the lifecycle execution.
        """
        return self._project_info.get_project_var(name, raw_read=raw_read)


class StepInfo:
    """Step-level information containing project, part, and step fields.

    :param part_info: The part information.
    :param step: The step we want to obtain information from.
    """

    def __init__(
        self,
        part_info: PartInfo,
        step: Step,
    ):
        self._part_info = part_info
        self.step = step
        self.step_environment: Dict[str, str] = {}

    def __getattr__(self, name):
        if hasattr(self._part_info, name):
            return getattr(self._part_info, name)

        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")


def _get_host_architecture() -> str:
    """Obtain the host system architecture."""
    # TODO: handle Windows architectures
    return platform.machine()


_ARCH_TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "aarch64": {
        "kernel": "arm64",
        "deb": "arm64",
        "uts_machine": "aarch64",
        "cross-compiler-prefix": "aarch64-linux-gnu-",
        "triplet": "aarch64-linux-gnu",
        "core-dynamic-linker": "lib/ld-linux-aarch64.so.1",
    },
    "armv7l": {
        "kernel": "arm",
        "deb": "armhf",
        "uts_machine": "arm",
        "cross-compiler-prefix": "arm-linux-gnueabihf-",
        "triplet": "arm-linux-gnueabihf",
        "core-dynamic-linker": "lib/ld-linux-armhf.so.3",
    },
    "i686": {
        "kernel": "x86",
        "deb": "i386",
        "uts_machine": "i686",
        "triplet": "i386-linux-gnu",
    },
    "ppc": {
        "kernel": "powerpc",
        "deb": "powerpc",
        "uts_machine": "powerpc",
        "cross-compiler-prefix": "powerpc-linux-gnu-",
        "triplet": "powerpc-linux-gnu",
    },
    "ppc64le": {
        "kernel": "powerpc",
        "deb": "ppc64el",
        "uts_machine": "ppc64el",
        "cross-compiler-prefix": "powerpc64le-linux-gnu-",
        "triplet": "powerpc64le-linux-gnu",
        "core-dynamic-linker": "lib64/ld64.so.2",
    },
    "riscv64": {
        "kernel": "riscv64",
        "deb": "riscv64",
        "uts_machine": "riscv64",
        "cross-compiler-prefix": "riscv64-linux-gnu-",
        "triplet": "riscv64-linux-gnu",
        "core-dynamic-linker": "lib/ld-linux-riscv64-lp64d.so.1",
    },
    "s390x": {
        "kernel": "s390",
        "deb": "s390x",
        "uts_machine": "s390x",
        "cross-compiler-prefix": "s390x-linux-gnu-",
        "triplet": "s390x-linux-gnu",
        "core-dynamic-linker": "lib/ld64.so.1",
    },
    "x86_64": {
        "kernel": "x86",
        "deb": "amd64",
        "uts_machine": "x86_64",
        "triplet": "x86_64-linux-gnu",
        "core-dynamic-linker": "lib64/ld-linux-x86-64.so.2",
    },
}
