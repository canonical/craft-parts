# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2024 Canonical Ltd.
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

"""Definitions and helpers to handle parts."""

import re
import warnings
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from craft_parts import errors, plugins
from craft_parts.constraints import RelativePathStr
from craft_parts.dirs import ProjectDirs
from craft_parts.features import Features
from craft_parts.packages import platform
from craft_parts.permissions import Permissions
from craft_parts.plugins.properties import PluginProperties
from craft_parts.steps import Step
from craft_parts.utils.partition_utils import get_partition_dir_map
from craft_parts.utils.path_utils import get_partition_and_path


class PartSpec(BaseModel):
    """The part specification data."""

    plugin: str | None = None
    source: str | None = None
    source_checksum: str = ""
    source_branch: str = ""
    source_commit: str = ""
    source_depth: int = 0
    source_subdir: str = ""
    source_submodules: list[str] | None = None
    source_tag: str = ""
    source_type: str = ""
    disable_parallel: bool = False
    after: list[str] = []
    overlay_packages: list[str] = []
    stage_snaps: list[str] = []
    stage_packages: list[str] = []
    build_snaps: list[str] = []
    build_packages: list[str] = []
    build_environment: list[dict[str, str]] = []
    build_attributes: list[str] = []
    organize_files: dict[str, str] = Field(default_factory=dict, alias="organize")
    overlay_files: list[str] = Field(default_factory=lambda: ["*"], alias="overlay")
    stage_files: list[RelativePathStr] = Field(
        default_factory=lambda: ["*"], alias="stage"
    )
    prime_files: list[RelativePathStr] = Field(
        default_factory=lambda: ["*"], alias="prime"
    )
    override_pull: str | None = None
    overlay_script: str | None = None
    override_build: str | None = None
    override_stage: str | None = None
    override_prime: str | None = None
    permissions: list[Permissions] = []

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        frozen=True,
        alias_generator=lambda s: s.replace("_", "-"),
        coerce_numbers_to_str=True,
    )

    @field_validator("overlay_packages", "overlay_files", "overlay_script")
    @classmethod
    def validate_overlay_feature(cls, item: Any) -> Any:  # noqa: ANN401
        """Check if overlay attributes specified when feature is disabled."""
        if not Features().enable_overlay:
            raise ValueError("overlays not supported")
        return item

    @model_validator(mode="before")
    @classmethod
    def validate_root(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Check if the part spec has a valid configuration of packages and slices."""
        if not platform.is_deb_based():
            # This check is only relevant in deb systems.
            return values

        def is_slice(name: str) -> bool:
            return "_" in name

        # Detect a mixture of .deb packages and chisel slices.
        stage_packages = values.get("stage-packages", [])
        has_slices = any(name for name in stage_packages if is_slice(name))
        has_packages = any(name for name in stage_packages if not is_slice(name))

        if has_slices and has_packages:
            raise ValueError("Cannot mix packages and slices in stage-packages")

        return values

    # pylint: enable=no-self-argument

    @classmethod
    def unmarshal(cls, data: dict[str, Any]) -> "PartSpec":
        """Create and populate a new ``PartSpec`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("part data is not a dictionary")

        return PartSpec(**data)

    def marshal(self) -> dict[str, Any]:
        """Create a dictionary containing the part specification data.

        :return: The newly created dictionary.

        """
        return self.model_dump(by_alias=True)

    def get_scriptlet(self, step: Step) -> str | None:
        """Return the scriptlet contents, if any, for the given step.

        :param step: the step corresponding to the scriptlet to be retrieved.

        :return: The scriptlet for the given step, if any.
        """
        if step == Step.PULL:
            return self.override_pull
        if step == Step.OVERLAY:
            return self.overlay_script
        if step == Step.BUILD:
            return self.override_build
        if step == Step.STAGE:
            return self.override_stage
        if step == Step.PRIME:
            return self.override_prime

        raise RuntimeError(f"cannot get scriptlet for invalid step {step!r}")

    @property
    def has_overlay(self) -> bool:
        """Return whether this spec declares overlay content."""
        return bool(
            self.overlay_packages
            or self.overlay_script is not None
            or self.overlay_files != ["*"]
        )

    @property
    def has_slices(self) -> bool:
        """Return whether the part contains chisel slices."""
        if not self.stage_packages:
            return False
        return any("_" in p for p in self.stage_packages)

    @property
    def has_chisel_as_build_snap(self) -> bool:
        """Return whether the part has chisel as build snap."""
        if not self.build_snaps:
            return False
        return any(
            p for p in self.build_snaps if p == "chisel" or p.startswith("chisel/")
        )


# pylint: disable=too-many-public-methods
class Part:
    """Each of the components used in the project specification.

    During the craft-parts lifecycle each part is processed through
    different steps in order to obtain its final artifacts. The Part
    class holds the part specification data and additional configuration
    information used during step processing.

    :param name: The part name.
    :param data: A dictionary containing the part properties.
    :param partitions: A Sequence of partition names if partitions are enabled, or None
    :param project_dirs: The project work directories.
    :param plugin_properties: An optional PluginProperties object for this plugin.

    :raise PartSpecificationError: If part validation fails.
    """

    def __init__(
        self,
        name: str,
        data: dict[str, Any],
        *,
        project_dirs: ProjectDirs | None = None,
        plugin_properties: "PluginProperties | None" = None,
        partitions: Sequence[str] | None = None,
    ) -> None:
        self._partitions = partitions
        if not isinstance(data, dict):
            raise errors.PartSpecificationError(
                part_name=name, message="part data is not a dictionary"
            )

        if not project_dirs:
            project_dirs = ProjectDirs(partitions=partitions)

        if not plugin_properties:
            try:
                plugin_properties = PluginProperties.unmarshal(data)
            except ValidationError as err:
                raise errors.PartSpecificationError.from_validation_error(
                    part_name=name, error_list=err.errors()
                ) from err

        plugin_name: str = data.get("plugin", "")

        self.name = name
        self.plugin_name = plugin_name
        self.plugin_properties = plugin_properties
        self.dirs = project_dirs
        self._part_dir = project_dirs.parts_dir / name
        self._part_dir = project_dirs.parts_dir / name

        try:
            self.spec = PartSpec.unmarshal(data)
        except ValidationError as err:
            raise errors.PartSpecificationError.from_validation_error(
                part_name=name, error_list=err.errors()
            ) from err

        self._check_partition_feature()
        self._check_partition_usage()

    def __repr__(self) -> str:
        return f"Part({self.name!r})"

    @property
    def parts_dir(self) -> Path:
        """Return the directory containing work files for each part."""
        return self.dirs.parts_dir

    @property
    def part_src_dir(self) -> Path:
        """Return the subdirectory containing the part source code."""
        return self._part_dir / "src"

    @property
    def part_src_subdir(self) -> Path:
        """Return the subdirectory in source containing the source subtree (if any)."""
        if self.spec.source_subdir:
            return self.part_src_dir / self.spec.source_subdir
        return self.part_src_dir

    @property
    def part_build_dir(self) -> Path:
        """Return the subdirectory containing the part build tree."""
        return self._part_dir / "build"

    @property
    def part_build_subdir(self) -> Path:
        """Return the subdirectory in build containing the source subtree (if any).

        Parts that have a source subdirectory and do not support out-of-source builds
        will have a build subdirectory.
        """
        if (
            self.plugin_name != ""
            and self.spec.source_subdir
            and not plugins.get_plugin_class(self.plugin_name).get_out_of_source_build()
        ):
            return self.part_build_dir / self.spec.source_subdir
        return self.part_build_dir

    @property
    def part_install_dir(self) -> Path:
        """Return the subdirectory to install the part build artifacts."""
        return self._part_dir / "install"

    @property
    def part_install_dirs(self) -> Mapping[str | None, Path]:
        """Return a mapping of partition names to install directories.

        With partitions disabled, the only partition name is ``None``
        """
        return MappingProxyType(
            get_partition_dir_map(
                base_dir=self.dirs.work_dir,
                partitions=self._partitions,
                suffix=f"parts/{self.name}/install",
            )
        )

    @property
    def part_state_dir(self) -> Path:
        """Return the subdirectory containing the part lifecycle state."""
        return self._part_dir / "state"

    @property
    def part_cache_dir(self) -> Path:
        """Return the subdirectory containing the part cache directory."""
        return self._part_dir / "cache"

    @property
    def part_packages_dir(self) -> Path:
        """Return the subdirectory containing the part stage packages directory."""
        return self._part_dir / "stage_packages"

    @property
    def part_snaps_dir(self) -> Path:
        """Return the subdirectory containing the part snap packages directory."""
        return self._part_dir / "stage_snaps"

    @property
    def part_run_dir(self) -> Path:
        """Return the subdirectory containing the part plugin scripts."""
        return self._part_dir / "run"

    @property
    def part_layer_dir(self) -> Path:
        """Return the subdirectory containing the part overlay files."""
        return self._part_dir / "layer"

    @property
    def overlay_dir(self) -> Path:
        """Return the overlay directory."""
        return self.dirs.overlay_dir

    @property
    def stage_dir(self) -> Path:
        """Return the staging area containing the installed files from all parts.

        If partitions are enabled, this is the stage directory for the default partition
        """
        return self.dirs.stage_dir

    @property
    def stage_dirs(self) -> Mapping[str | None, Path]:
        """A mapping of partition name to partition staging directory.

        If partitions are disabled, the only key is ``None``.
        """
        return self.dirs.stage_dirs

    @property
    def prime_dir(self) -> Path:
        """Return the primed tree containing the artifacts to deploy.

        If partitions are enabled, this is the prime directory for the default partition
        """
        return self.dirs.prime_dir

    @property
    def prime_dirs(self) -> Mapping[str | None, Path]:
        """A mapping of partition name to partition prime directory.

        If partitions are disabled, the only key is ``None``.
        """
        return self.dirs.prime_dirs

    @property
    def dependencies(self) -> list[str]:
        """Return the list of parts this part depends on."""
        if not self.spec.after:
            return []
        return self.spec.after

    @property
    def has_overlay(self) -> bool:
        """Return whether this part declares overlay content."""
        return self.spec.has_overlay

    @property
    def has_slices(self) -> bool:
        """Return whether this part has slices in its stage-packages."""
        return self.spec.has_slices

    @property
    def has_chisel_as_build_snap(self) -> bool:
        """Return whether this part has chisel in its build-snaps."""
        return self.spec.has_chisel_as_build_snap

    def _check_partition_feature(self) -> None:
        """Check if the partitions feature is properly used.

        :raises FeatureError: If partitions are defined but the feature is not enabled.
        """
        if self._partitions and not Features().enable_partitions:
            raise errors.FeatureError(
                "Partitions specified but partitions feature is not enabled."
            )

        if self._partitions is None and Features().enable_partitions:
            raise errors.FeatureError(
                "Partitions feature is enabled but no partitions specified."
            )

    def _check_partition_usage(self) -> None:
        """Check if partitions are properly used in a part.

        Assumes the partition feature is enabled.

        :raises PartitionError: If partitions are not used properly in a fileset.
        :raises PartitionWarning: If a fileset entry is misusing a partition.
        """
        if not self._partitions:
            return

        error_list: list[str] = []
        warning_list: list[str] = []

        for fileset_name, fileset, require_inner_path in [
            # organize source entries do not use partitions and
            # organize destination entries do not require an inner path
            ("organize", self.spec.organize_files.values(), False),
            ("stage", self.spec.stage_files, True),
            ("prime", self.spec.prime_files, True),
        ]:
            partition_warnings, partition_errors = self._check_partitions_in_filepaths(
                fileset_name, fileset, require_inner_path=require_inner_path
            )
            warning_list.extend(partition_warnings)
            error_list.extend(partition_errors)

        if warning_list:
            warnings.warn(
                errors.PartitionUsageWarning(warning_list=warning_list), stacklevel=1
            )

        if error_list:
            raise errors.PartitionUsageError(
                error_list=error_list,
                partitions=self._partitions,
            )

    def _check_partitions_in_filepaths(
        self, fileset_name: str, fileset: Iterable[str], *, require_inner_path: bool
    ) -> tuple[list[str], list[str]]:
        """Check if partitions are properly used in a fileset.

        If a filepath begins with a parentheses, then the text inside the parentheses
        must be a valid partition. This is an error.

        Some filesets must specify a path to avoid ambiguity. For example, the
        following is not allowed:
            stage:
              - (default)
              - (default)/
        Whereas the organize destination does not require an inner path:
            organize:
              - foo: (mypart)

        If a path begins with a partition name but is not encapsulated in parentheses,
        a warning is generated. This will not warn for misuses of namespaced partitions.

        :param fileset_name: The name of the fileset being checked.
        :param fileset: The list of filepaths to check.
        :param require_inner_path: True if entries in the fileset need an inner path.

        :returns: A tuple containing two lists:
            - A list of warnings of possible misuses of partitions in the fileset
            - A list of invalid uses of partitions in the fileset
        """
        error_list: list[str] = []
        warning_list: list[str] = []

        if not self._partitions:
            return warning_list, error_list

        partition_pattern = re.compile("^-?\\((?P<partition>.*?)\\)")
        possible_partition_pattern = re.compile("^-?(?P<possible_partition>[a-z]+)/?")

        for filepath in fileset:
            match = re.match(partition_pattern, filepath)
            if match:
                partition = match.group("partition")
                if str(partition) not in self._partitions:
                    error_list.append(
                        f"    unknown partition {partition!r} in {filepath!r}"
                    )
            else:
                match = re.match(possible_partition_pattern, filepath)
                if match:
                    partition = match.group("possible_partition")
                    if partition in self._partitions:
                        warning_list.append(
                            f"    misused partition {partition!r} in {filepath!r}"
                        )

            if require_inner_path:
                _, inner_path = get_partition_and_path(filepath)
                if not inner_path:
                    error_list.append(
                        f"    no path specified after partition in {filepath!r}"
                    )

        if error_list:
            error_list.insert(0, f"  parts.{self.name}.{fileset_name}")
        if warning_list:
            warning_list.insert(0, f"  parts.{self.name}.{fileset_name}")

        return warning_list, error_list


# pylint: enable=too-many-public-methods


def part_by_name(name: str, part_list: list[Part]) -> Part:
    """Obtain the part with the given name from the part list.

    :param name: The name of the part to return.
    :param part_list: The list of all known parts.

    :returns: The part with the given name.
    """
    for part in part_list:
        if part.name == name:
            return part

    raise errors.InvalidPartName(name)


def part_list_by_name(names: Sequence[str] | None, part_list: list[Part]) -> list[Part]:
    """Return a list of parts from part_list that are named in names.

    :param names: The list of part names. If the list is empty or not
        defined, return all parts from part_list.
    :param part_list: The list of all known parts.

    :returns: The list of parts corresponding to the given names.

    :raises InvalidPartName: if a part name is not defined.
    """
    if names:
        # check if all part names are valid
        valid_names = {p.name for p in part_list}
        for name in names:
            if name not in valid_names:
                raise errors.InvalidPartName(name)

        selected_parts = [p for p in part_list if p.name in names]
    else:
        selected_parts = part_list

    return selected_parts


def sort_parts(part_list: list[Part]) -> list[Part]:
    """Perform an inefficient but easy to follow sorting of parts.

    :param part_list: The list of parts to sort.

    :returns: The sorted list of parts.

    :raises PartDependencyCycle: if there are circular dependencies.
    """
    sorted_parts: list[Part] = []

    # We want to process parts in a consistent order between runs. The
    # simplest way to do this is to sort them by name.
    all_parts = sorted(part_list, key=lambda part: part.name, reverse=True)

    while all_parts:
        top_part = None

        for part in all_parts:
            mentioned = False
            for other in all_parts:
                if part.name in other.dependencies:
                    mentioned = True
                    break
            if not mentioned:
                top_part = part
                break
        if not top_part:
            raise errors.PartDependencyCycle

        sorted_parts = [top_part, *sorted_parts]
        all_parts.remove(top_part)

    return sorted_parts


def part_dependencies(
    part: Part, *, part_list: list[Part], recursive: bool = False
) -> set[Part]:
    """Return a set of all the parts upon which the named part depends.

    :param part: The dependent part.

    :returns: The set of parts the given part depends on.
    """
    dependency_names = set(part.dependencies)
    dependencies = {p for p in part_list if p.name in dependency_names}

    if recursive:
        # No need to worry about infinite recursion due to circular
        # dependencies since the YAML validation won't allow it.
        for dependency_name in dependency_names:
            dep = part_by_name(dependency_name, part_list=part_list)
            dependencies |= part_dependencies(
                dep, part_list=part_list, recursive=recursive
            )

    return dependencies


def has_overlay_visibility(
    part: Part, *, part_list: list[Part], viewers: set[Part] | None = None
) -> bool:
    """Check if a part can see the overlay filesystem.

    A part that declares overlay parameters and all parts depending on it
    are granted permission to see overlay filesystem.

    :param part: The part whose overlay visibility will be checked.
    :param viewers: Parts that are known to have overlay visibility.
    :param part_list: A list of all parts in the project.

    :return: Whether the part has overlay visibility.
    """
    if (viewers and part in viewers) or part.has_overlay:
        return True

    if not part.spec.after:
        return False

    deps = part_dependencies(part, part_list=part_list)
    for dep in deps:
        if has_overlay_visibility(dep, viewers=viewers, part_list=part_list):
            return True

    return False


def get_parts_with_overlay(*, part_list: list[Part]) -> list[Part]:
    """Obtain a list of parts that declare overlay parameters.

    :param part_list: A list of all parts in the project.

    :return: A list of parts with overlay parameters.
    """
    return [p for p in part_list if p.has_overlay]


def validate_part(data: dict[str, Any]) -> None:
    """Validate the given part data against common and plugin models.

    :param data: The part data to validate.
    """
    _get_part_spec(data)


def part_has_overlay(data: dict[str, Any]) -> bool:
    """Whether the part described by ``data`` employs the Overlay step.

    :param data: The part data to query for overlay use.
    """
    spec = _get_part_spec(data)

    return spec.has_overlay


def part_has_slices(data: dict[str, Any]) -> bool:
    """Whether the part described by ``data`` contains slices.

    :param data: The part data to query.
    """
    spec = _get_part_spec(data)

    return spec.has_slices


def part_has_chisel_as_build_snap(data: dict[str, Any]) -> bool:
    """Whether the part described by ``data`` has chisel in build-snaps.

    :param data: The part data to query.
    """
    spec = _get_part_spec(data)

    return spec.has_chisel_as_build_snap


def _get_part_spec(data: dict[str, Any]) -> PartSpec:
    if not isinstance(data, dict):
        raise TypeError("value must be a dictionary")

    # copy the original data, we'll modify it
    spec = data.copy()

    plugin_name = spec.get("plugin")
    if not plugin_name:
        raise ValueError("'plugin' not defined")

    plugin_class = plugins.get_plugin_class(plugin_name)

    # validate plugin properties
    plugin_class.properties_class.unmarshal(spec)

    # validate common part properties
    part_spec = plugins.extract_part_properties(spec, plugin_name=plugin_name)
    return PartSpec(**part_spec)
