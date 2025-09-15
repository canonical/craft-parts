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

"""Project, part and step information classes."""

from __future__ import annotations

import logging
import platform
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

import pydantic
from typing_extensions import Self

from craft_parts import errors
from craft_parts.dirs import ProjectDirs
from craft_parts.filesystem_mounts import (
    FilesystemMount,
    FilesystemMountItem,
    FilesystemMounts,
)
from craft_parts.utils.partition_utils import DEFAULT_PARTITION, is_default_partition

if TYPE_CHECKING:
    from collections.abc import Sequence, ValuesView

    from craft_parts.parts import Part
    from craft_parts.state_manager import states
    from craft_parts.steps import Step

logger = logging.getLogger(__name__)

# Architecture name translation from platform to deb/snap.
_PLATFORM_MACHINE_TO_DEB = {
    "aarch64": "arm64",
    "armv7l": "armhf",
    "i686": "i386",
    "ppc": "powerpc",
    "ppc64le": "ppc64el",
    "x86_64": "amd64",
    "AMD64": "amd64",  # Windows support
}


# Equivalent platform machine values.
_PLATFORM_MACHINE_VARIATIONS: dict[str, str] = {
    "AMD64": "x86_64",
    "ARM64": "aarch64",
    "amd64": "x86_64",
    "arm64": "aarch64",
    "armv7hl": "armv7l",
    "armv8l": "armv7l",
    "i386": "i686",
    "x64": "x86_64",
}


# Debian architecture to cpu-vendor-os platform triplet.
_DEB_TO_TRIPLET: dict[str, str] = {
    "amd64": "x86_64-linux-gnu",
    "arm64": "aarch64-linux-gnu",
    "armhf": "arm-linux-gnueabihf",
    "i386": "i386-linux-gnu",
    "powerpc": "powerpc-linux-gnu",
    "ppc64el": "powerpc64le-linux-gnu",
    "riscv64": "riscv64-linux-gnu",
    "s390x": "s390x-linux-gnu",
}


_var_name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ProjectVar(pydantic.BaseModel):
    """A project variable that can be updated using craftctl."""

    model_config = pydantic.ConfigDict(
        validate_assignment=True,
        extra="forbid",
        alias_generator=lambda s: s.replace("_", "-"),
        populate_by_name=True,
    )

    value: Annotated[
        str | None,
        pydantic.Field(
            # to handle unquoted versions
            coerce_numbers_to_str=True,
        ),
    ] = None
    """The value of the project variable."""

    updated: bool = False
    """Whether the variable has already been updated."""

    part_name: str | None = None
    """The name of the part that can update the project variable."""

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> ProjectVar:
        """Create and populate a new ProjectVar object from a dict.

        The unmarshal method validates entries in the input dict, populating
        the corresponding fields in the data object.

        :param data: The dict to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dict.
        :raise pydantic.ValidationError: If the data fails validation.
        """
        if not isinstance(data, dict):
            raise TypeError("Project variable must be a dictionary.")

        return cls.model_validate(data)

    def marshal(self, attr: str | None = None) -> dict[str, Any] | str | bool | None:
        """Create a dictionary containing the project var data.

        :param attr: If provided, return the bare attribute instead of a
            dictionary of all attributes.

        :return: The newly created dictionary or a specific attribute.
        """
        if attr:
            return cast(str | bool | None, getattr(self, attr))

        return self.model_dump(mode="json", by_alias=True)


class ProjectVarInfo(pydantic.RootModel):
    """Project variables that can be updated using craftctl.

    This class wraps a nested dictionary of project variables.
    Data is accessed with structured paths.
    """

    root: dict[str, ProjectVar | ProjectVarInfo] = {}
    """A nested dictionary of ProjectVars."""

    def __getitem__(self, key: str) -> ProjectVar | ProjectVarInfo:
        return self.root[key]

    def __setitem__(self, key: str, value: ProjectVar | ProjectVarInfo) -> None:
        self.root[key] = value

    def values(self) -> ValuesView[ProjectVar | ProjectVarInfo]:
        """Get values of the project vars."""
        return self.root.values()

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> ProjectVarInfo:
        """Create and populate a new ProjectVarInfo object from a dict.

        The unmarshal method validates entries in the input dict, populating
        the corresponding fields in the data object.

        :param data: The dict to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dict.
        :raise pydantic.ValidationError: If the data fails validation.
        """
        if not isinstance(data, dict):
            raise TypeError("Project variable info must be a dictionary.")

        return cls.model_validate(data)

    def marshal(self, attr: str | None = None) -> dict[str, Any]:
        """Create a dictionary containing the project var info data.

        :param attr: The name of a ProjectVar attribute to return in place
            of the ProjectVar itself. This is useful for:
            - the StateManager in craft-parts which only needs part names
            - a PackageService in a downstream application which only needs values

        :return: The newly created dictionary.
        """
        if not attr:
            return cast(dict[str, Any], self.model_dump(mode="json", by_alias=True))

        result: dict[str, Any] = {}
        for key, value in self.root.items():
            result[key] = value.marshal(attr)
        return result

    def has_key(self, *keys: str) -> bool:
        """Check if a key exists.

        :param keys: A structured path to the value.

        :returns: True if the key exists in the dictionary.

        :raises KeyError: If no keys are provided.
        """
        logger.debug(f"Checking if {ProjectVarInfo._format_keys(*keys)!r} exists.")
        self._validate_keys(*keys)

        try:
            self.get(*keys)
        except (KeyError, ValueError):
            logger.debug(f"{ProjectVarInfo._format_keys(*keys)!r} doesn't exist.")
            return False

        logger.debug(f"{ProjectVarInfo._format_keys(*keys)!r} exists.")
        return True

    def get(self, *keys: str) -> ProjectVar:
        """Get the ProjectVar at a given path.

        :param keys: A structured path to the value.

        :returns: The value for the key.

        :raises KeyError: If an item in the path doesn't exist.
        :raises KeyError: If an item in the path isn't a dictionary.
        :raises KeyError: If no keys are provided.
        :raises ValueError: If the keys don't lead to a ProjectVar.
        """
        logger.debug(f"Getting value for {ProjectVarInfo._format_keys(*keys)!r}.")
        self._validate_keys(*keys)

        try:
            value = self._get(*keys, data=self)
        except (ValueError, KeyError) as err:
            raise type(err)(
                f"Failed to get value for {ProjectVarInfo._format_keys(*keys)!r}: {err.args[0]}"
            ) from err

        logger.debug(
            f"Got {value.value!r} (updated={value.updated}) for {ProjectVarInfo._format_keys(*keys)!r}."
        )
        return value

    def _get(self, *keys: str, data: ProjectVarInfo) -> ProjectVar:
        """Recursive helper to get a ProjectVar from a nested dictionary.

        :param keys: A structured path to the value. At least one key must be provided.
        :param data: The dictionary to recurse into.

        :returns: The value for the key.

        :raises KeyError: If an item in the path doesn't exist.
        :raises KeyError: If an item in the path isn't a dictionary.
        :raises ValueError: If the keys don't lead to a ProjectVar.
        """
        key, *remaining = keys

        try:
            data_at_key = data[key]
        except KeyError as err:
            raise KeyError(f"{key!r} doesn't exist.") from err

        if len(keys) == 1:
            if not isinstance(data_at_key, ProjectVar):
                raise ValueError("value isn't a ProjectVar.")
            return data_at_key

        if not isinstance(data_at_key, ProjectVarInfo):
            raise KeyError(f"can't traverse into node at {key!r}.")

        return self._get(*remaining, data=data_at_key)

    def set(self, *keys: str, value: str, overwrite: bool = False) -> None:
        """Set a ProjectVar at a given path.

        :param keys: A structured path to the value.
        :param value: The value to set.
        :param overwrite: Allow overwriting existing values.

        :raises KeyError: If an item in the path isn't a dictionary.
        :raises KeyError: If no keys are provided.
        :raises ValueError: If the ProjectVar has already been updated and 'overwrite' is false.
        :raises ValueError: If the keys don't lead to a ProjectVar.
        """
        logger.debug(f"Setting {ProjectVarInfo._format_keys(*keys)!r} to {value!r}.")
        self._validate_keys(*keys)

        try:
            self._set(*keys, data=self, value=value, overwrite=overwrite)
        except (KeyError, ValueError) as err:
            raise type(err)(
                f"Failed to set {ProjectVarInfo._format_keys(*keys)!r} to {value!r}: {err.args[0]}"
            ) from err

        logger.debug(f"Set {ProjectVarInfo._format_keys(*keys)!r} to {value!r}.")

    def _set(
        self,
        *keys: str,
        data: ProjectVarInfo,
        value: str,
        overwrite: bool,
    ) -> None:
        """Recursive helper to set a ProjectVar in a nested dictionary.

        :param keys: A structured path to the value. At least one key must be provided.
        :param data: The data structure to recurse into.
        :param value: The value to set.
        :param overwrite: Allow overwriting existing values.

        :raises KeyError: If an item in the path isn't a dictionary.
        :raises ValueError: If the ProjectVar has already been updated and 'overwrite' is false.
        :raises ValueError: If the keys don't lead to a ProjectVar.
        """
        key, *remaining = keys

        try:
            data_at_key = data[key]
        except KeyError as err:
            raise KeyError(f"{key!r} doesn't exist.") from err

        if len(keys) == 1:
            if not isinstance(data_at_key, ProjectVar):
                raise ValueError("value isn't a ProjectVar.")

            if data_at_key.updated:
                if overwrite:
                    logger.debug(f"Overwriting updated value {data_at_key.value!r}.")
                else:
                    raise ValueError(
                        f"key {key!r} already exists and overwrite is false."
                    )

            data_at_key.updated = True
            data_at_key.value = value
            return

        if not isinstance(data_at_key, ProjectVarInfo):
            raise KeyError(f"can't traverse into node at {key!r}.")

        self._set(*remaining, data=data_at_key, value=value, overwrite=overwrite)

    def update_from(self, other: ProjectVarInfo, part_name: str) -> None:
        """Update ProjectVars from another ProjectVarInfo instance for a particular part.

        This is useful when updating the Lifecycle's ProjectVarInfo with data from a state file.

        :param part_name: Only ProjectVars with this part name are updated.

        :raises TypeError: If the structure is not identical.
        """
        for key, other_value in other.root.items():
            self_value = self.root.get(key)

            if isinstance(self_value, ProjectVar) and isinstance(
                other_value, ProjectVar
            ):
                if other_value.updated and other_value.part_name == part_name:
                    self_value.value = other_value.value
                    self_value.updated = True
            elif isinstance(self_value, ProjectVarInfo) and isinstance(
                other_value, ProjectVarInfo
            ):
                self_value.update_from(other_value, part_name)
            else:
                raise TypeError(
                    "Cannot update ProjectVarInfo because the structure doesn't match."
                )

    def _validate_keys(self, *keys: str) -> None:
        """Validate the keys.

        :raises KeyError: If no keys are provided.
        """
        if not keys:
            raise KeyError("No keys provided.")

    @staticmethod
    def _format_keys(*keys: str) -> str:
        """Format keys in dot notation."""
        return ".".join(keys)


# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class ProjectInfo:
    """Project-level information containing project-specific fields.

    :param application_name: A unique identifier for the application using
        Craft Parts.
    :param project_name: Name of the project being built.
    :param cache_dir: The path to store cached packages and files. If not
        specified, a directory under the application name entry in the XDG
        base directory will be used.
    :param arch: The architecture to build for. Defaults to the host system
        architecture.
    :param parallel_build_count: The maximum number of concurrent jobs to be
        used to build each part of this project.
    :param strict_mode: Only allow plugins capable of building in strict mode.
    :param project_dirs: The project work directories.
    :param project_name: The name of the project.
    :param project_vars_part_name: Project variables can be set only if
        the part name matches this name.
    :param project_vars: A nested dictionary containing project variables and the
        part that can update each variable. Project variables can also be defined with
        a deprecated API where `project_vars` must be a flat (not-nested) dictionary and
        `project_vars_part_name` defines the part that can update all project variables.
    :param custom_args: Any additional arguments defined by the application
        when creating a :class:`LifecycleManager`.
    :param partitions: A list of partitions.
    :param filesystem_mounts: A dict of filesystem_mounts.
    :param usrmerged_by_default: Whether the parts' install dirs should be filled with
        usrmerge-safe directories and symlinks prior to a part's build.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        application_name: str,
        cache_dir: Path,
        arch: str = "",
        base: str = "",
        parallel_build_count: int = 1,
        strict_mode: bool = False,
        project_dirs: ProjectDirs | None = None,
        project_name: str | None = None,
        project_vars_part_name: str | None = None,
        project_vars: dict[str, str] | ProjectVarInfo | None = None,
        partitions: list[str] | None = None,
        filesystem_mounts: FilesystemMounts | None = None,
        base_layer_dir: Path | None = None,
        base_layer_hash: bytes | None = None,
        usrmerged_by_default: bool = False,
        **custom_args: Any,  # custom passthrough args
    ) -> None:
        if arch and arch not in _DEB_TO_TRIPLET:
            raise errors.InvalidArchitecture(arch)

        if not project_dirs:
            project_dirs = ProjectDirs(partitions=partitions)

        self._application_name = application_name
        self._cache_dir = Path(cache_dir).expanduser().resolve()
        self._host_arch = _get_host_architecture()
        self._arch = arch or self._host_arch
        self._base = base  # base usage is deprecated
        self._parallel_build_count = parallel_build_count
        self._strict_mode = strict_mode
        self._dirs = project_dirs
        self._project_name = project_name
        self._project_vars_part_name = project_vars_part_name
        self._project_vars = self._get_project_var_info(
            project_vars, project_vars_part_name
        )
        self._partitions = partitions
        self._filesystem_mounts = filesystem_mounts
        self._custom_args = custom_args
        self._base_layer_dir = base_layer_dir
        self._base_layer_hash = base_layer_hash
        self.global_environment: dict[str, str] = {}
        self._usrmerged_by_default = usrmerged_by_default

        self.execution_finished = False

    def _get_project_var_info(
        self,
        project_vars: dict[str, str] | ProjectVarInfo | None,
        part_name: str | None,
    ) -> ProjectVarInfo:
        """Get a ProjectVarInfo.

        :param project_vars: Either a ProjectVarInfo instance or a dictionary containing
        project variables. The latter type is deprecated.
        :param part_name: The name of the part that can set the variables. This is a deprecated
        parameter and is ignored when using a ProjectVarInfo is provided.

        :returns: A ProjectVarInfo instance.

        :raises RuntimeError: If the deprecated API is mixed with the new API.
        """
        if isinstance(project_vars, ProjectVarInfo):
            if part_name:
                raise RuntimeError(
                    "Cannot handle 'project_vars' of type ProjectVarInfo and 'project_vars_part_name'. "
                    "Do not provide the deprecated 'project_vars_part_name' parameter."
                )
            return project_vars

        if project_vars:
            warnings.warn(
                DeprecationWarning(
                    "Using deprecated API to define project variables. "
                    "Provide ProjectVarInfo instead."
                ),
                stacklevel=2,
            )

        return ProjectVarInfo.unmarshal(
            {
                key: ProjectVar(value=value, part_name=part_name).marshal()
                for key, value in (project_vars or {}).items()
            }
        )

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        if hasattr(self._dirs, name):
            return getattr(self._dirs, name)

        if name in self._custom_args:
            return self._custom_args[name]

        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")

    @property
    def custom_args(self) -> list[str]:
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
    def arch_build_on(self) -> str:
        """The architecture we are building on."""
        return self._host_arch

    @property
    def arch_build_for(self) -> str:
        """The architecture we are building for."""
        return self._arch

    @property
    def arch_triplet_build_on(self) -> str:
        """The machine-vendor-os triplet for the platform we are building on."""
        return _DEB_TO_TRIPLET[self._host_arch]

    @property
    def arch_triplet_build_for(self) -> str:
        """The machine-vendor-os triplet for the platform we are building for."""
        return _DEB_TO_TRIPLET[self._arch]

    @property
    def arch_triplet(self) -> str:
        """Return the machine-vendor-os platform triplet definition."""
        return _DEB_TO_TRIPLET[self._arch]

    @property
    def is_cross_compiling(self) -> bool:
        """Whether the target and host architectures are different."""
        return self._arch != self._host_arch

    @property
    def parallel_build_count(self) -> int:
        """Return the maximum allowable number of concurrent build jobs."""
        return self._parallel_build_count

    @property
    def strict_mode(self) -> bool:
        """Return whether this project must be built in 'strict' mode."""
        return self._strict_mode

    @property
    def host_arch(self) -> str:
        """Return the host architecture used for debs, snaps and charms."""
        return self._host_arch

    @property
    def target_arch(self) -> str:
        """Return the target architecture used for debs, snaps and charms."""
        return self._arch

    @property
    def base(self) -> str:
        """Return the project build base."""
        return self._base

    @property
    def dirs(self) -> ProjectDirs:
        """Return the project's work directories."""
        return self._dirs

    @property
    def project_name(self) -> str | None:
        """Return the name of the project using craft-parts."""
        return self._project_name

    @property
    def project_vars(self) -> ProjectVarInfo:
        """Return the project vars."""
        return self._project_vars

    @property
    def project_vars_part_name(self) -> str | None:
        """Return the name of the part that can set project vars."""
        warnings.warn(
            DeprecationWarning(
                "'ProjectInfo.project_vars_part_name' is deprecated. "
                "Use 'ProjectInfo.project_vars' instead."
            ),
            stacklevel=2,
        )
        return self._project_vars_part_name

    @property
    def project_options(self) -> dict[str, Any]:
        """Obtain a project-wide options dictionary."""
        return {
            "application_name": self.application_name,
            "arch_triplet": self.arch_triplet,
            "target_arch": self.target_arch,
            "project_vars_part_name": self._project_vars_part_name,
            "project_vars": self._project_vars,
        }

    @property
    def partitions(self) -> list[str] | None:
        """Return the project's partitions."""
        return self._partitions

    @property
    def default_partition(self) -> str | None:
        """Get the "default" partition from a partition list."""
        if self._partitions:
            return self._partitions[0]
        return None

    @property
    def is_default_partition_aliased(self) -> bool:
        """Check if the default partition is aliased."""
        return (
            self._partitions is not None and self.default_partition != DEFAULT_PARTITION
        )

    @property
    def alias_partition_dir(self) -> Path | None:
        """Partition directory for the default alias partition."""
        if not self.is_default_partition_aliased:
            return None
        if not self.default_partition:
            return None
        return self._dirs.work_dir / "partitions" / self.default_partition

    @property
    def parts_alias_symlink(self) -> Path | None:
        """Parts directory for the default alias partition."""
        if self.alias_partition_dir:
            return self.alias_partition_dir / "parts"
        return None

    @property
    def stage_alias_symlink(self) -> Path | None:
        """Stage directory for the default alias partition."""
        if alias_partition_dir := self.alias_partition_dir:
            return alias_partition_dir / "stage"
        return None

    @property
    def prime_alias_symlink(self) -> Path | None:
        """Prime directory for the default alias partition."""
        if alias_partition_dir := self.alias_partition_dir:
            return alias_partition_dir / "prime"
        return None

    @property
    def overlay_alias_symlink(self) -> Path | None:
        """Overlay directory for the default alias partition."""
        if alias_partition_dir := self.alias_partition_dir:
            return alias_partition_dir / "overlay"
        return None

    def is_default_partition(self, partition: str | None) -> bool:
        """Check if given partition is the default one."""
        return is_default_partition(self._partitions, partition)

    @property
    def filesystem_mounts(self) -> FilesystemMounts | None:
        """Return the project's filesystem mounts."""
        return self._filesystem_mounts

    @property
    def default_filesystem_mount(self) -> FilesystemMount:
        """Return the project's default filesystem mount."""
        if self._filesystem_mounts:
            default_filesytem_mount = self._filesystem_mounts.get("default")
            if default_filesytem_mount:
                return default_filesytem_mount

        return FilesystemMount(root=[FilesystemMountItem(mount="/", device="default")])

    @property
    def base_layer_dir(self) -> Path | None:
        """Return the directory containing the base layer (if any)."""
        return self._base_layer_dir

    @property
    def base_layer_hash(self) -> bytes | None:
        """Return the hash of the base layer (if any)."""
        return self._base_layer_hash

    @property
    def usrmerged_by_default(self) -> bool:
        """Return whether parts should be usrmerged by default."""
        return self._usrmerged_by_default

    def set_project_var(
        self,
        name: str,
        value: str,
        raw_write: bool = False,  # noqa: FBT001, FBT002
        *,
        part_name: str | None = None,
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
        keys = name.split(".")
        project_var = self._project_vars.get(*keys)

        if raw_write:
            self._project_vars.set(*keys, value=value, overwrite=raw_write)
            return

        if project_var.updated:
            raise RuntimeError(f"variable {name!r} can be set only once")

        if project_var.part_name == part_name:
            self._project_vars.set(*keys, value=value)
        elif not project_var.part_name:
            raise RuntimeError(
                f"variable {name!r} can only be set in a part that "
                "adopts external metadata"
            )
        else:
            raise RuntimeError(
                f"variable {name!r} can only be set in part {project_var.part_name!r}"
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

        return self._project_vars.get(*name.split(".")).value or ""

    def _ensure_valid_variable_name(self, name: str) -> None:
        """Raise an error if variable name is invalid.

        :param name: The variable name to verify.
        """
        for item in name.split("."):
            if not _var_name_pattern.match(item):
                raise ValueError(f"{name!r} is not a valid variable name")

        if not self._project_vars.has_key(*name.split(".")):
            raise ValueError(f"{name!r} not in project variables")


class ProjectOptions(pydantic.BaseModel):
    """A collection of project-wide options.

    :param application_name: A unique identifier for the application using
        Craft Parts.
    :param arch_triplet: Concatenated cpu-vendor-os platform.
    :param target_arch: The architecture to build for.
    :param project_vars: A dictionary containing the project variables.
    :param project_vars_part_name: Project variables can be set only if
        the part name matches this name.
    """

    application_name: str = ""
    arch_triplet: str = ""
    target_arch: str = ""
    project_vars_part_name: str | None = None
    project_vars: ProjectVarInfo = ProjectVarInfo()

    @classmethod
    def from_project_info(cls, project_info: ProjectInfo) -> Self:
        """Construct a ProjectOptions instance from a ProjectInfo instance.

        :param project_info: The project information.
        """
        return cls.model_validate(project_info.project_options)


class PartInfo:
    """Part-level information containing project and part fields.

    :param project_info: The project information.
    :param part: The part we want to obtain information from.
    """

    def __init__(
        self,
        project_info: ProjectInfo,
        part: Part,
    ) -> None:
        self._project_info = project_info
        self._part_name = part.name
        self._part_src_dir = part.part_src_dir
        self._part_src_subdir = part.part_src_subdir
        self._part_build_dir = part.part_build_dir
        self._part_build_subdir = part.part_build_subdir
        self._part_export_dir = part.part_export_dir
        self._part_install_dir = part.part_install_dir
        self._part_state_dir = part.part_state_dir
        self._part_cache_dir = part.part_cache_dir
        self._part_dependencies = part.dependencies
        self._plugin_name = part.plugin_name
        self.build_attributes = part.spec.build_attributes.copy()

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
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
    def part_export_dir(self) -> Path:
        """Return the subdirectory for internal artifact output."""
        return self._part_export_dir

    @property
    def part_install_dir(self) -> Path:
        """Return the subdirectory to install the part's build artifacts."""
        return self._part_install_dir

    @property
    def part_state_dir(self) -> Path:
        """Return the subdirectory containing this part's lifecycle state."""
        return self._part_state_dir

    @property
    def part_cache_dir(self) -> Path:
        """Return the subdirectory containing this part's cache directory."""
        return self._part_cache_dir

    @property
    def part_dependencies(self) -> Sequence[str]:
        """Return the names of the parts that this part depends on."""
        return self._part_dependencies

    @property
    def plugin_name(self) -> str:
        """Return the name of the part's plugin."""
        return self._plugin_name

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
    ) -> None:
        self._part_info = part_info
        self.step = step
        self.step_environment: dict[str, str] = {}
        self.state: states.StepState | None = None

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        if hasattr(self._part_info, name):
            return getattr(self._part_info, name)

        raise AttributeError(f"{self.__class__.__name__!r} has no attribute {name!r}")


def _get_host_architecture() -> str:
    """Obtain the host system architecture."""
    machine = platform.machine()
    machine = _PLATFORM_MACHINE_VARIATIONS.get(machine, machine)
    return _PLATFORM_MACHINE_TO_DEB.get(machine, machine)
