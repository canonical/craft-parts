# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021,2024 Canonical Ltd.
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

"""Definitions and helpers to handle filesets."""

import os
from glob import iglob
from typing import List, Optional, Set, Tuple

from craft_parts import errors, features
from craft_parts.utils import path_utils


class Fileset:
    """A class that represents a list of filepath strings to include or exclude.

    Filepaths to include do not begin with a hyphen.
    Filepaths to exclude begin with a hyphen.
    """

    def __init__(self, entries: List[str], *, name: str = "") -> None:
        """Initialize a fileset.

        If the partition feature is enabled, files in the default partition are
        normalized to begin with `(default)/`. For example, ["foo", "(default)/bar"]
        is normalized to ["(default)/foo", "(default)/bar"].

        :param entries: List of filepaths represented as strings.
        :param name: Name of the fileset.

        :raises FilesetError: If any entry is an absolute filepath.
        """
        self._name = name
        self._validate_entries(entries)
        self._list: List[str] = [_normalize_entry(entry) for entry in entries]

    def __repr__(self) -> str:
        return f"Fileset({self._list!r}, name={self._name!r})"

    @property
    def name(self) -> str:
        """Return the fileset name."""
        return self._name

    @property
    def entries(self) -> List[str]:
        """Return the list of entries in this fileset."""
        return self._list.copy()

    @property
    def includes(self) -> List[str]:
        """Return the list of files to be included."""
        return [x for x in self._list if x[0] != "-"]

    @property
    def excludes(self) -> List[str]:
        """Return the list of files to be excluded."""
        return [x[1:] for x in self._list if x[0] == "-"]

    def remove(self, item: str) -> None:
        """Remove this entry from the list of files.

        :param item: The item to remove.
        """
        self._list.remove(_normalize_entry(item))

    def combine(self, other: "Fileset") -> None:
        """Combine the entries in this fileset with entries from another fileset.

        :param other: The fileset to combine with.
        """
        to_combine = False
        # combine if the fileset has a wildcard
        if "*" in self.entries:
            to_combine = True
            self.remove("*")

        other_excludes = set(other.excludes)
        my_includes = set(self.includes)

        contradicting_set = set.intersection(other_excludes, my_includes)
        if contradicting_set:
            raise errors.FilesetConflict(contradicting_set)

        # combine if the fileset is only excludes
        if {x[0] for x in self.entries} == set("-"):
            to_combine = True

        if to_combine:
            self._list = list(set(self._list + other.entries))

    def _validate_entries(self, entries: List[str]) -> None:
        """Validate that entries are not absolute filepaths.

        :param entries: List of entries to validate.

        :raises FilesetError: If `entries` contains an absolute filepath.
        """
        for entry in entries:
            filepath = entry[1:] if entry[0] == "-" else entry
            if os.path.isabs(filepath):
                raise errors.FilesetError(
                    name=self.name, message=f"path {filepath!r} must be relative."
                )


def migratable_filesets(
    fileset: Fileset, srcdir: str, partition: Optional[str] = None
) -> Tuple[Set[str], Set[str]]:
    """Determine the files to migrate from a directory based on a fileset.

    :param fileset: The fileset used to filter files in the srcdir.
    :param srcdir: Directory containing files to migrate.
    :param partition: If provided, only get files to migrate to the partition.

    :return: A tuple containing the set of files and the set of directories to migrate.
    """
    includes, excludes = _get_file_list(fileset, partition)

    include_files = _generate_include_set(srcdir, includes)
    exclude_files, exclude_dirs = _generate_exclude_set(srcdir, excludes)

    files = include_files - exclude_files
    for exclude_dir in exclude_dirs:
        files = {x for x in files if not x.startswith(exclude_dir + "/")}

    # Separate dirs from files.
    dirs = {
        x
        for x in files
        if os.path.isdir(os.path.join(srcdir, x))
        and not os.path.islink(os.path.join(srcdir, x))
    }

    # Remove dirs from files.
    files = files - dirs

    # Include (resolved) parent directories for each selected file.
    for _filename in files:
        filename = _get_resolved_relative_path(_filename, srcdir)
        dirname = os.path.dirname(filename)
        while dirname:
            dirs.add(dirname)
            dirname = os.path.dirname(dirname)

    # Resolve parent paths for dirs and files.
    resolved_dirs = set()
    for dirname in dirs:
        resolved_dirs.add(_get_resolved_relative_path(dirname, srcdir))

    resolved_files = set()
    for filename in files:
        resolved_files.add(_get_resolved_relative_path(filename, srcdir))

    return resolved_files, resolved_dirs


def _get_file_list(
    fileset: Fileset, partition: Optional[str]
) -> Tuple[List[str], List[str]]:
    """Split a fileset to obtain include and exclude file filters.

    If the fileset does not include any files, then the include list will contain a
        single wildcard: ["*"].

    :param fileset: The fileset to split.
    :param partition: If provided, only get the file list for files in the partition.

    :return: A tuple containing the include and exclude lists.

    :raises FeatureError: If the partition feature is enabled but no partition is
        provided or if a partition is provided but the partition feature is not enabled.
    """
    if features.Features().enable_partitions and not partition:
        raise errors.FeatureError(
            message=(
                "A partition must be provided if the partition feature is enabled."
            )
        )

    if not features.Features().enable_partitions and partition:
        raise errors.FeatureError(
            message=(
                "The partition feature must be enabled if a partition is provided."
            )
        )

    includes: List[str] = []
    excludes: List[str] = []

    for item in fileset.entries:
        if item.startswith("-"):
            excludes.append(item[1:])
        elif item.startswith("\\"):
            includes.append(item[1:])
        else:
            includes.append(item)

    # short circuit if no partition was provided
    if not partition:
        return includes or ["*"], excludes

    # only include files for the partition
    processed_includes: List[str] = []
    for file in includes:
        file_partition, file_inner_path = path_utils.get_partition_and_path(file)
        if file_partition == partition:
            processed_includes.append(str(file_inner_path))

    # only exclude files for the partition
    processed_excludes: List[str] = []
    for file in excludes:
        file_partition, file_inner_path = path_utils.get_partition_and_path(file)
        if file_partition == partition:
            processed_excludes.append(str(file_inner_path))

    # the default behavior is to include everything
    return processed_includes or ["*"], processed_excludes


def _generate_include_set(directory: str, includes: List[str]) -> Set[str]:
    """Obtain the list of files to include based on include file filter.

    :param directory: The path to the tree containing the files to filter.

    :return: The set of files to include.
    """
    include_files = set()

    for include in includes:
        if "*" in include:
            pattern = os.path.join(directory, include)
            matches = iglob(pattern, recursive=True)
            include_files |= set(matches)
        else:
            include_files |= {os.path.join(directory, include)}

    include_dirs = [
        x for x in include_files if os.path.isdir(x) and not os.path.islink(x)
    ]
    include_files = {os.path.relpath(x, directory) for x in include_files}

    # Expand includeFiles, so that an exclude like '*/*.so' will still match
    # files from an include like 'lib'
    for include_dir in include_dirs:
        for root, dirs, files in os.walk(include_dir):
            include_files |= {
                os.path.relpath(os.path.join(root, d), directory) for d in dirs
            }
            include_files |= {
                os.path.relpath(os.path.join(root, f), directory) for f in files
            }

    return include_files


def _generate_exclude_set(
    directory: str, excludes: List[str]
) -> Tuple[Set[str], Set[str]]:
    """Obtain the list of files to exclude based on exclude file filter.

    :param directory: The path to the tree containing the files to filter.

    :return: The set of files to exclude.
    """
    exclude_files = set()

    for exclude in excludes:
        pattern = os.path.join(directory, exclude)
        matches = iglob(pattern, recursive=True)
        exclude_files |= set(matches)

    exclude_dirs = {
        os.path.relpath(x, directory) for x in exclude_files if os.path.isdir(x)
    }
    exclude_files = {os.path.relpath(x, directory) for x in exclude_files}

    return exclude_files, exclude_dirs


def _get_resolved_relative_path(relative_path: str, base_directory: str) -> str:
    """Resolve path components against target base_directory.

    If the resulting target path is a symlink, it will not be followed.
    Only the path's parents are fully resolved against base_directory,
    and the relative path is returned.

    :param relative_path: Path of target, relative to base_directory.
    :param base_directory: Base path of target.

    :return: Resolved path, relative to base_directory.
    """
    parent_relpath, filename = os.path.split(relative_path)
    parent_abspath = os.path.realpath(os.path.join(base_directory, parent_relpath))

    filename_abspath = os.path.join(parent_abspath, filename)
    return os.path.relpath(filename_abspath, base_directory)


def _normalize_entry(entry: str) -> str:
    """Normalize an entry to begin with a partition, if partitions are enabled.

    If partitions are enabled, `foo` will be normalized to `(default)/foo`.
    If partitions are not enabled, `foo` will be left as `foo`.

    :param entry: Entry to normalize.

    :returns: Normalized entry.
    """
    # split file into an optional prefix (a hyphen character) and the file
    split_file = (entry[0], entry[1:]) if entry[0] == "-" else ("", entry)

    partition, inner_path = path_utils.get_partition_and_path(split_file[1])

    if partition:
        return f"{split_file[0]}({partition})/{inner_path}"

    return entry
