# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2015-2021 Canonical Ltd.
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
import pathlib

from craft_parts import errors
from craft_parts.utils import path_utils


class Fileset:
    """Helper class to process string lists."""

    def __init__(self, entries: list[str], *, name: str = "") -> None:
        self._name = name
        self._list = entries

    def __repr__(self) -> str:
        return f"Fileset({self._list!r}, name={self._name!r})"

    @property
    def name(self) -> str:
        """Return the fileset name."""
        return self._name

    @property
    def entries(self) -> list[str]:
        """Return the list of entries in this fileset."""
        return self._list.copy()

    @property
    def includes(self) -> list[str]:
        """Return the list of files to be included."""
        return [path_utils.get_partitioned_path(x) for x in self._list if x[0] != "-"]

    @property
    def excludes(self) -> list[str]:
        """Return the list of files to be excluded."""
        return [
            path_utils.get_partitioned_path(x[1:]) for x in self._list if x[0] == "-"
        ]

    def remove(self, item: str) -> None:
        """Remove this entry from the list of files.

        :param item: The item to remove.
        """
        self._list.remove(item)

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


def migratable_filesets(
    fileset: Fileset, srcdir: pathlib.Path
) -> tuple[set[str], set[str]]:
    """Return the files and directories that can be migrated.

    :param fileset: The fileset to migrate.

    :return: A tuple containing the set of files and the set of directories
        that can be migrated.
    """
    includes, excludes = _get_file_list(fileset)

    include_files = _generate_include_set(srcdir, includes)
    exclude_files, exclude_dirs = _generate_exclude_set(srcdir, excludes)

    files = include_files - exclude_files
    for exclude_dir in exclude_dirs:
        files = {x for x in files if exclude_dir not in x.parents}

    # Separate dirs from files.
    dirs = {x for x in files if (srcdir / x).is_dir() and not (srcdir / x).is_symlink()}

    # Remove dirs from files.
    files = files - dirs

    # Include (resolved) parent directories for each selected file.
    for _filename in files:
        filename = pathlib.Path(_filename)
        filename = _get_resolved_relative_path(filename, srcdir)
        dirname = filename.parent
        while dirname != dirname.parent:
            dirs.add(dirname)
            dirname = dirname.parent
        dirs.add(dirname)

    # Resolve parent paths for dirs and files.
    resolved_dirs = set()
    for dirname in dirs:
        resolved_dirs.add(_get_resolved_relative_path(dirname, srcdir))

    resolved_files = set()
    for filename in files:
        resolved_files.add(_get_resolved_relative_path(filename, srcdir))

    return {str(_file) for _file in resolved_files}, {
        str(_dir) for _dir in resolved_dirs
    }


def _get_file_list(fileset: Fileset) -> tuple[list[str], list[str]]:
    """Split a fileset to obtain include and exclude file filters.

    :param fileset: The fileset to split.

    :return: A tuple containing the include and exclude lists.
    """
    includes: list[str] = []
    excludes: list[str] = []

    for item in fileset.entries:
        if item.startswith("-"):
            excludes.append(item[1:])
        elif item.startswith("\\"):
            includes.append(item[1:])
        else:
            includes.append(item)

    # paths must be relative
    for entry in includes + excludes:
        if pathlib.Path(entry).is_absolute():
            raise errors.FilesetError(
                name=fileset.name, message=f"path {entry!r} must be relative."
            )

    includes = includes or ["*"]

    processed_includes: list[str] = []
    processed_excludes: list[str] = []
    for file in includes:
        processed_includes.append(path_utils.get_partitioned_path(file))
    for file in excludes:
        processed_excludes.append(path_utils.get_partitioned_path(file))
    return processed_includes, processed_excludes


def _generate_include_set(
    directory: pathlib.Path, includes: list[str]
) -> set[pathlib.Path]:
    """Obtain the list of files to include based on include file filter.

    :param directory: The path to the tree containing the files to filter.

    :return: The set of files to include.
    """
    include_files: set[pathlib.Path] = set()

    for include in includes:
        if "*" in include:
            matches = directory.rglob(include)
            include_files |= set(matches)
        else:
            include_files |= {directory / include}

    include_dirs = [x for x in include_files if x.is_dir() and not x.is_symlink()]
    include_files = {x.relative_to(directory) for x in include_files}

    # Expand includeFiles, so that an exclude like '*/*.so' will still match
    # files from an include like 'lib'
    for include_dir in include_dirs:
        for root, dirs, files in os.walk(include_dir):
            include_files |= {
                (pathlib.Path(root) / d).relative_to(directory) for d in dirs
            }
            include_files |= {
                (pathlib.Path(root) / f).relative_to(directory) for f in files
            }

    return include_files


def _generate_exclude_set(
    directory: pathlib.Path, excludes: list[str]
) -> tuple[set[pathlib.Path], set[pathlib.Path]]:
    """Obtain the list of files to exclude based on exclude file filter.

    :param directory: The path to the tree containing the files to filter.

    :return: The set of files to exclude.
    """
    exclude_files: set[pathlib.Path] = set()

    for exclude in excludes:
        matches = directory.rglob(exclude)
        exclude_files |= set(matches)

    exclude_dirs = {
        pathlib.Path(x).relative_to(directory) for x in exclude_files if x.is_dir()
    }
    exclude_files = {pathlib.Path(x).relative_to(directory) for x in exclude_files}

    return exclude_files, exclude_dirs


def _get_resolved_relative_path(
    relative_path: pathlib.Path, base_directory: pathlib.Path
) -> pathlib.Path:
    """Resolve path components against target base_directory.

    If the resulting target path is a symlink, it will not be followed.
    Only the path's parents are fully resolved against base_directory,
    and the relative path is returned.

    :param relative_path: Path of target, relative to base_directory.
    :param base_directory: Base path of target.

    :return: Resolved path, relative to base_directory.
    """
    parent_abspath = (base_directory / relative_path.parent).resolve()

    file_abspath = parent_abspath / relative_path.name
    return file_abspath.relative_to(base_directory)
