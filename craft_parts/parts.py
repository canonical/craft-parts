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

"""Definitions and helpers to handle parts."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from pydantic import BaseModel, Field, ValidationError, root_validator, validator

from craft_parts import errors, plugins
from craft_parts.dirs import ProjectDirs
from craft_parts.packages import platform
from craft_parts.plugins.properties import PluginProperties
from craft_parts.steps import Step


class PartSpec(BaseModel):
    """The part specification data."""

    plugin: Optional[str] = None
    source: Optional[str] = None
    source_checksum: str = ""
    source_branch: str = ""
    source_commit: str = ""
    source_depth: int = 0
    source_subdir: str = ""
    source_submodules: Optional[List[str]] = None
    source_tag: str = ""
    source_type: str = ""
    disable_parallel: bool = False
    after: List[str] = []
    overlay_packages: List[str] = []
    stage_snaps: List[str] = []
    stage_packages: List[str] = []
    build_snaps: List[str] = []
    build_packages: List[str] = []
    build_environment: List[Dict[str, str]] = []
    build_attributes: List[str] = []
    organize_files: Dict[str, str] = Field({}, alias="organize")
    overlay_files: List[str] = Field(["*"], alias="overlay")
    stage_files: List[str] = Field(["*"], alias="stage")
    prime_files: List[str] = Field(["*"], alias="prime")
    override_pull: Optional[str] = None
    overlay_script: Optional[str] = None
    override_build: Optional[str] = None
    override_stage: Optional[str] = None
    override_prime: Optional[str] = None

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "forbid"
        allow_mutation = False
        alias_generator = lambda s: s.replace("_", "-")  # noqa: E731

    # pylint: disable=no-self-argument
    @validator("stage_files", "prime_files", each_item=True)
    def validate_relative_path_list(cls, item):
        """Check if the list does not contain empty of absolute paths."""
        assert item != "", "path cannot be empty"
        assert (
            item[0] != "/"
        ), f"{item!r} must be a relative path (cannot start with '/')"
        return item

    @root_validator(pre=True)
    def validate_root(cls, values):
        """Check if the part spec has a valid configuration of packages and slices."""
        if not platform.is_deb_based():
            # This check is only relevant in deb systems.
            return values

        def is_slice(name):
            return "_" in name

        # Detect a mixture of .deb packages and chisel slices.
        stage_packages = values.get("stage-packages", [])
        has_slices = any(name for name in stage_packages if is_slice(name))
        has_packages = any(name for name in stage_packages if not is_slice(name))

        assert not (
            has_slices and has_packages
        ), "Cannot mix packages and slices in stage-packages"

        return values

    # pylint: enable=no-self-argument

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "PartSpec":
        """Create and populate a new ``PartSpec`` object from dictionary data.

        The unmarshal method validates entries in the input dictionary, populating
        the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal.

        :return: The newly created object.

        :raise TypeError: If data is not a dictionary.
        """
        if not isinstance(data, dict):
            raise TypeError("part data is not a dictionary")

        spec = PartSpec(**data)

        return spec

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the part specification data.

        :return: The newly created dictionary.

        """
        return self.dict(by_alias=True)

    def get_scriptlet(self, step: Step) -> Optional[str]:
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
        if step == step.PRIME:
            return self.override_prime

        raise RuntimeError(f"cannot get scriptlet for invalid step {step!r}")


class Part:
    """Each of the components used in the project specification.

    During the craft-parts lifecycle each part is processed through
    different steps in order to obtain its final artifacts. The Part
    class holds the part specification data and additional configuration
    information used during step processing.

    :param name: The part name.
    :param data: A dictionary containing the part properties.
    :param project_dirs: The project work directories.

    :raise PartSpecificationError: If part validation fails.
    """

    def __init__(
        self,
        name: str,
        data: Dict[str, Any],
        *,
        project_dirs: Optional[ProjectDirs] = None,
        plugin_properties: "Optional[PluginProperties]" = None,
    ):
        if not isinstance(data, dict):
            raise errors.PartSpecificationError(
                part_name=name, message="part data is not a dictionary"
            )

        if not project_dirs:
            project_dirs = ProjectDirs()

        if not plugin_properties:
            plugin_properties = PluginProperties()

        plugin_name: str = data.get("plugin", "")

        self.name = name
        self.plugin_name = plugin_name
        self.plugin_properties = plugin_properties
        self._dirs = project_dirs
        self._part_dir = project_dirs.parts_dir / name
        self._part_dir = project_dirs.parts_dir / name

        try:
            self.spec = PartSpec.unmarshal(data)
        except ValidationError as err:
            raise errors.PartSpecificationError.from_validation_error(
                part_name=name, error_list=err.errors()
            )

    def __repr__(self):
        return f"Part({self.name!r})"

    @property
    def parts_dir(self) -> Path:
        """Return the directory containing work files for each part."""
        return self._dirs.parts_dir

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
    def part_state_dir(self) -> Path:
        """Return the subdirectory containing the part lifecycle state."""
        return self._part_dir / "state"

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
        return self._dirs.overlay_dir

    @property
    def stage_dir(self) -> Path:
        """Return the staging area containing the installed files from all parts."""
        return self._dirs.stage_dir

    @property
    def prime_dir(self) -> Path:
        """Return the primed tree containing the artifacts to deploy."""
        return self._dirs.prime_dir

    @property
    def dependencies(self) -> List[str]:
        """Return the list of parts this part depends on."""
        if not self.spec.after:
            return []
        return self.spec.after

    @property
    def has_overlay(self) -> bool:
        """Return whether this part declares overlay content."""
        return bool(
            self.spec.overlay_packages
            or self.spec.overlay_script is not None
            or self.spec.overlay_files != ["*"]
        )


def part_by_name(name: str, part_list: List[Part]) -> Part:
    """Obtain the part with the given name from the part list.

    :param name: The name of the part to return.
    :param part_list: The list of all known parts.

    :returns: The part with the given name.
    """
    for part in part_list:
        if part.name == name:
            return part

    raise errors.InvalidPartName(name)


def part_list_by_name(
    names: Optional[Sequence[str]], part_list: List[Part]
) -> List[Part]:
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


def sort_parts(part_list: List[Part]) -> List[Part]:
    """Perform an inneficient but easy to follow sorting of parts.

    :param part_list: The list of parts to sort.

    :returns: The sorted list of parts.

    :raises PartDependencyCycle: if there are circular dependencies.
    """
    sorted_parts = []  # type: List[Part]

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
            raise errors.PartDependencyCycle()

        sorted_parts = [top_part] + sorted_parts
        all_parts.remove(top_part)

    return sorted_parts


def part_dependencies(
    part: Part, *, part_list: List[Part], recursive: bool = False
) -> Set[Part]:
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
    part: Part, *, part_list: List[Part], viewers: Optional[Set[Part]] = None
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


def get_parts_with_overlay(*, part_list: List[Part]) -> List[Part]:
    """Obtain a list of parts that declare overlay parameters.

    :param part_list: A list of all parts in the project.

    :return: A list of parts with overlay parameters.
    """
    return [p for p in part_list if p.has_overlay]


def validate_part(data: Dict[str, Any]) -> None:
    """Validate the given part data against common and plugin models.

    :param data: The part data to validate.
    """
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
    PartSpec(**part_spec)
