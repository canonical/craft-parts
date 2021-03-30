# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

"""Project, part and step information classes."""

import logging
import platform
from typing import Any, Dict, List

from craft_parts import errors, utils
from craft_parts.dirs import ProjectDirs

logger = logging.getLogger(__name__)


class ProjectInfo:
    """Project-level information containing project-specific fields.

    :param application_name: A unique identifier for the application using
        Craft Parts.
    :param arch: The architecture to build for. Defaults to the host system
        architecture.
    :param parallel_build_count: The maximum number of concurrent jobs to be
        used to build each part of this project.
    :param plugin_version: The plugin API version. Currently only ``v2`` is
        supported.
    :param project_dirs: The project work directories.
    :param custom_args: Any additional arguments defined by the application
        when creating a :class:`LifecycleManager`.
    """

    def __init__(
        self,
        *,
        application_name: str = utils.package_name(),
        arch: str = "",
        parallel_build_count: int = 1,
        plugin_version: str = "v2",
        project_dirs: ProjectDirs = None,
        **custom_args,  # custom passthrough args
    ):
        if not project_dirs:
            project_dirs = ProjectDirs()

        self._application_name = application_name
        self._set_machine(arch)
        self._plugin_version = plugin_version
        self._parallel_build_count = parallel_build_count
        self._dirs = project_dirs
        self._custom_args = custom_args

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
    def arch_triplet(self) -> str:
        """Return the machine-vendor-os platform triplet definition."""
        return self.__machine_info["triplet"]

    @property
    def is_cross_compiling(self) -> bool:
        """Whether the target and host architectures are different."""
        return self.__target_machine != self.__platform_arch

    @property
    def plugin_version(self) -> str:
        """Return the plugin API version used in this project."""
        return self._plugin_version

    @property
    def parallel_build_count(self) -> int:
        """Return the maximum allowable number of concurrent build jobs."""
        return self._parallel_build_count

    @property
    def target_arch(self) -> str:
        """Return the architecture used for debs, snaps and charms."""
        return self.__machine_info["deb"]

    @property
    def dirs(self) -> ProjectDirs:
        """Return the project's work directories."""
        return self._dirs

    @property
    def project_options(self) -> Dict[str, Any]:
        """Obtain a project-wide options dictionary."""
        return {
            "application_name": self.application_name,
            "arch_triplet": self.arch_triplet,
            "target_arch": self.target_arch,
        }

    def _set_machine(self, target_arch):
        self.__platform_arch = _get_platform_architecture()
        if not target_arch:
            target_arch = self.__platform_arch
            logger.debug("Setting target machine to %s", target_arch)

        machine = _ARCH_TRANSLATIONS.get(target_arch, None)
        if not machine:
            raise errors.InvalidArchitecture(target_arch)

        self.__target_machine = target_arch
        self.__machine_info = machine


def _get_platform_architecture() -> str:
    # TODO: handle Windows architectures
    return platform.machine()


_ARCH_TRANSLATIONS = {
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
