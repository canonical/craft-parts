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
from glob import iglob
from typing import List, Set, Tuple

from craft_parts import errors


class Fileset:
    """Helper class to process string lists."""

    def __init__(self, entries: List[str], *, name: str = ""):
        self._name = name
        self._list = entries

    def __repr__(self):
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
        self._list.remove(item)

    def combine(self, other: "Fileset") -> None:
        """Combine the entries in this fileset with entries from another fileset.

        :param other: The fileset to combine with.
        """
        to_combine = False
        # combine if the fileset has a wildcard
        # XXX: should this only be a single wildcard and possibly excludes?
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


def migratable_filesets(fileset: Fileset, srcdir: str) -> Tuple[Set[str], Set[str]]:
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
    for filename in files:
        filename = _get_resolved_relative_path(filename, srcdir)
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


def _get_file_list(fileset: Fileset) -> Tuple[List[str], List[str]]:
    """Split a fileset to obtain include and exclude file filters.

    :param fileset: The fileset to split.

    :return: A tuple containing the include and exclude lists.
    """
    includes: List[str] = []
    excludes: List[str] = []

    for item in fileset.entries:
        if item.startswith("-"):
            excludes.append(item[1:])
        elif item.startswith("\\"):
            includes.append(item[1:])
        else:
            includes.append(item)

    # paths must be relative
    for entry in includes + excludes:
        if os.path.isabs(entry):
            raise errors.FilesetError(
                name=fileset.name, message=f"path {entry!r} must be relative."
            )

    includes = includes or ["*"]

    return includes, excludes


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
            include_files |= set([os.path.join(directory, include)])

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
    filename_relpath = os.path.relpath(filename_abspath, base_directory)

    return filename_relpath
