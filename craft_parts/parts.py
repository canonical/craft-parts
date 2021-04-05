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

"""Definitions and helpers to handle parts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from craft_parts import errors, unmarshal
from craft_parts.dirs import ProjectDirs
from craft_parts.steps import Step


@dataclass(frozen=True)
class PartSpec:
    """The part specification data."""

    plugin: Optional[str]
    source: Optional[str]
    source_checksum: str
    source_branch: str
    source_commit: str
    source_depth: int
    source_subdir: str
    source_tag: str
    source_type: str
    disable_parallel: bool
    after: List[str]
    stage_snaps: List[str]
    stage_packages: List[str]
    build_snaps: List[str]
    build_packages: List[str]
    build_environment: List[Dict[str, str]]
    build_attributes: List[str]
    organize_fileset: Dict[str, str]
    stage_fileset: List[str]
    prime_fileset: List[str]
    override_pull: Optional[str]
    override_build: Optional[str]
    override_stage: Optional[str]
    override_prime: Optional[str]

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "PartSpec":
        """Create and populate a new ``PartSpec`` object from dictionary data.

        The unmarshal method validates and consumes entries in the input
        dictionary, populating the corresponding fields in the data object.

        :param data: The dictionary data to unmarshal and consume.

        :return: The newly created object.

        :raise ValueError: If data validation fails.
        """
        if not isinstance(data, dict):
            raise ValueError("part data is not a dictionary")

        udata = unmarshal.DataUnmarshaler(data)

        return cls(
            plugin=udata.pop_optional_string("plugin"),
            source=udata.pop_optional_string("source"),
            source_checksum=udata.pop_string("source-checksum"),
            source_branch=udata.pop_string("source-branch"),
            source_commit=udata.pop_string("source-commit"),
            source_depth=udata.pop_integer("source-depth"),
            source_subdir=udata.pop_string("source-subdir"),
            source_tag=udata.pop_string("source-tag"),
            source_type=udata.pop_string("source-type"),
            disable_parallel=udata.pop_boolean("disable-parallel"),
            after=udata.pop_list_str("after", []),
            stage_snaps=udata.pop_list_str("stage-snaps", []),
            stage_packages=udata.pop_list_str("stage-packages", []),
            build_snaps=udata.pop_list_str("build-snaps", []),
            build_packages=udata.pop_list_str("build-packages", []),
            build_environment=udata.pop_list_dict("build-environment", []),
            build_attributes=udata.pop_list_str("build-attributes", []),
            organize_fileset=udata.pop_dict("organize", {}),
            stage_fileset=udata.pop_list_str("stage", ["*"]),
            prime_fileset=udata.pop_list_str("prime", ["*"]),
            override_pull=udata.pop_optional_string("override-pull"),
            override_build=udata.pop_optional_string("override-build"),
            override_stage=udata.pop_optional_string("override-stage"),
            override_prime=udata.pop_optional_string("override-prime"),
        )

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the part specification data.

        :return: The newly created dictionary.

        """
        return {
            "plugin": self.plugin,
            "source": self.source,
            "source-checksum": self.source_checksum,
            "source-branch": self.source_branch,
            "source-commit": self.source_commit,
            "source-depth": self.source_depth,
            "source-subdir": self.source_subdir,
            "source-tag": self.source_tag,
            "source-type": self.source_type,
            "disable-parallel": self.disable_parallel,
            "after": self.after,
            "stage-snaps": self.stage_snaps,
            "stage-packages": self.stage_packages,
            "build-snaps": self.build_snaps,
            "build-packages": self.build_packages,
            "build-environment": self.build_environment,
            "build-attributes": self.build_attributes,
            "organize": self.organize_fileset,
            "stage": self.stage_fileset,
            "prime": self.prime_fileset,
            "override-pull": self.override_pull,
            "override-build": self.override_build,
            "override-stage": self.override_stage,
            "override-prime": self.override_prime,
        }

    def get_scriptlet(self, step: Step) -> Optional[str]:
        """Return the scriptlet contents, if any, for the given step.

        :param step: the step corresponding to the scriptlet to be retrieved.

        :return: The scriptlet for the given step, if any.
        """
        return {
            Step.PULL: self.override_pull,
            Step.BUILD: self.override_build,
            Step.STAGE: self.override_stage,
            Step.PRIME: self.override_prime,
        }[step]


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
        project_dirs: ProjectDirs = None,
    ):
        if not isinstance(data, dict):
            raise errors.PartSpecificationError(
                part_name=name, message="part data is not a dictionary"
            )

        if not project_dirs:
            project_dirs = ProjectDirs()

        plugin_name: str = data.get("plugin", "")

        self.name = name
        self.plugin = plugin_name
        self._dirs = project_dirs
        self._part_dir = project_dirs.parts_dir / name
        self._part_dir = project_dirs.parts_dir / name

        try:
            self.spec = PartSpec.unmarshal(data)
        except ValueError as err:
            raise errors.PartSpecificationError(part_name=name, message=str(err))

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
        return self.part_src_dir / self.spec.source_subdir

    @property
    def part_build_dir(self) -> Path:
        """Return the subdirectory containing the part build tree."""
        return self._part_dir / "build"

    @property
    def part_build_subdir(self) -> Path:
        """Return the subdirectory in build containing the source subtree (if any)."""
        return self.part_build_dir / self.spec.source_subdir

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
        return self.spec.after


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
    name: str, *, part_list: List[Part], recursive: bool = False
) -> Set[Part]:
    """Return a set of all the parts upon which the named part depends.

    :param name: The name of the dependent part.

    :returns: The set of parts the given part depends on.

    :raises InvalidPartName: if a part name is not defined.
    """
    part = next((p for p in part_list if p.name == name), None)
    if not part:
        raise errors.InvalidPartName(name)

    dependency_names = set(part.dependencies)
    dependencies = {p for p in part_list if p.name in dependency_names}

    if recursive:
        # No need to worry about infinite recursion due to circular
        # dependencies since the YAML validation won't allow it.
        for dependency_name in dependency_names:
            dependencies |= part_dependencies(
                dependency_name, part_list=part_list, recursive=recursive
            )

    return dependencies
