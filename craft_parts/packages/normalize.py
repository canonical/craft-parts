# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2017-2021 Canonical Ltd.
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

"""Definition and helpers for the repository base class."""

import contextlib
import fileinput
import itertools
import logging
import os
import re
import shutil
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Pattern

if TYPE_CHECKING:
    from .base import RepositoryType


logger = logging.getLogger(__name__)


def normalize(unpack_dir: Path, *, repository: "RepositoryType") -> None:
    """Normalize unpacked artifacts.

    Repository-specific packages are generally created to live in a specific
    distro. Normalize scans through the unpacked artifacts and slightly modifies
    them to work better in the Craft Parts build environment.

    :param unpack_dir: Directory containing unpacked files to normalize.
    :param repository: The package format handler.
    """
    _remove_useless_files(unpack_dir)
    _fix_artifacts(unpack_dir, repository)
    _fix_xml_tools(unpack_dir)
    _fix_shebangs(unpack_dir)


def _remove_useless_files(unpack_dir: Path) -> None:
    """Remove files that aren't useful or will clash with other parts.

    :param unpack_dir: Directory containing unpacked files to normalize.
    """
    sitecustomize_files = Path(unpack_dir, "usr", "lib").glob(
        "python*/sitecustomize.py"
    )

    for sitecustomize_file in sitecustomize_files:
        sitecustomize_file.unlink()


def _fix_artifacts(unpack_dir: Path, repository: "RepositoryType") -> None:
    """Perform various modifications to unpacked artifacts.

    Sometimes distro packages will contain absolute symlinks (e.g. if the
    relative path would go all the way to root, they just do absolute). We
    can't have that, so instead clean those absolute symlinks.

    Some unpacked items will also contain suid binaries which we do not
    want in the resulting environment.

    :param unpack_dir: Directory containing unpacked files to normalize.
    """
    logger.debug("fix artifacts: unpack_dir=%r", str(unpack_dir))

    for root, dirs, files in os.walk(unpack_dir):
        # Symlinks to directories will be in dirs, while symlinks to
        # non-directories will be in files.
        for entry in itertools.chain(files, dirs):
            path = Path(root, entry)
            if path.is_symlink() and Path(os.readlink(path)).is_absolute():
                _fix_symlink(path, unpack_dir, Path(root), repository)
            elif path.exists():
                _fix_filemode(path)

            if path.name.endswith(".pc") and path.is_file() and not path.is_symlink():
                fix_pkg_config(unpack_dir, path)


def _fix_xml_tools(unpack_dir: Path) -> None:
    """Adjust the path in XML tools.

    :param unpack_dir: Directory containing unpacked files to normalize.
    """
    xml2_config_path = unpack_dir / "usr" / "bin" / "xml2-config"
    with contextlib.suppress(FileNotFoundError):
        _search_and_replace_contents(
            xml2_config_path,
            re.compile(r"prefix=/usr"),
            f"prefix={unpack_dir}/usr",
        )

    xslt_config_path = unpack_dir / "usr" / "bin" / "xslt-config"
    with contextlib.suppress(FileNotFoundError):
        _search_and_replace_contents(
            xslt_config_path,
            re.compile(r"prefix=/usr"),
            f"prefix={unpack_dir}/usr",
        )


def _fix_symlink(
    path: Path, unpack_dir: Path, root: Path, repository: "RepositoryType"
) -> None:
    logger.debug(
        "fix symlink: path=%r, unpack_dir=%r, root=%r",
        str(path),
        str(unpack_dir),
        str(root),
    )
    host_target = os.readlink(path)
    if host_target in repository.get_package_libraries("libc6"):
        logger.debug("Not fixing symlink %s: it's pointing to libc", host_target)
        return

    target = unpack_dir / os.readlink(path)[1:]
    logger.debug("fix symlink: target=%r", str(target))

    if not target.exists() and not _try_copy_local(path, target):
        return
    path.unlink()

    # Path.relative_to() requires self to be the subpath of the argument,
    # but os.path.relpath() does not.
    path.symlink_to(os.path.relpath(target, start=root))


def _fix_shebangs(unpack_dir: Path) -> None:
    """Change hard-coded shebangs in unpacked files to use env."""
    _rewrite_python_shebangs(unpack_dir)


def _try_copy_local(path: Path, target: Path) -> bool:
    real_path = path.resolve()
    if real_path.exists():
        logger.warning("Copying needed target link from the system: %s", real_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.readlink(path), target)
        return True

    logger.warning("%s will be a dangling symlink", path)
    return False


def fix_pkg_config(
    prefix_prepend: Path, pkg_config_file: Path, prefix_trim: Optional[Path] = None
) -> None:
    """Fix the prefix parameter in pkg-config files.

    This function does 3 things:
    1. Remove `prefix_trim` from the prefix.
    2. Remove directories commonly added by staged snaps from the prefix.
    3. Prepend `prefix_prepend` to the prefix.

    The prepended stage directory depends on the source of the pkg-config file:
    - From snaps built via launchpad: `/build/<snap-name>/stage`
    - From snaps built via a provider: `/root/stage`
    - From snaps built locally: `<local-path-to-project>/stage`
    - Built during the build stage: the install directory

    :param pkg_config_file: pkg-config (.pc) file to modify
    :param prefix_prepend: directory to prepend to the prefix
    :param prefix_trim: directory to remove from prefix
    """
    # build patterns
    prefixes_to_trim = [r"/build/[\w\-. ]+/stage", "/root/stage"]
    if prefix_trim:
        prefixes_to_trim.append(prefix_trim.as_posix())
    pattern_trim = re.compile(
        f"^prefix=(?P<trim>{'|'.join(prefixes_to_trim)})(?P<prefix>.*)"
    )
    pattern = re.compile("^prefix=(?P<prefix>.*)")

    # process .pc file
    with fileinput.input(pkg_config_file, inplace=True) as input_file:
        for line in input_file:
            match = pattern.search(line)
            match_trim = pattern_trim.search(line)

            if match_trim is not None:
                # trim prefix and prepend new data
                new_prefix = f"prefix={prefix_prepend}{match_trim.group('prefix')}"
            elif match:
                # nothing to trim, so only prepend new data
                new_prefix = f"prefix={prefix_prepend}{match.group('prefix')}"
            else:
                new_prefix = None
                print(line, end="")

            if new_prefix is not None:
                print(new_prefix)
                logger.debug(
                    "For pkg-config file %s, prefix was changed from %s to %s",
                    pkg_config_file,
                    line,
                    new_prefix.strip(),
                )


def _fix_filemode(path: Path) -> None:
    mode = stat.S_IMODE(path.lstat().st_mode)
    if mode & 0o4000 or mode & 0o2000:
        logger.warning("Removing suid/guid from %s", path)
        path.chmod(mode & 0o1777)


def _rewrite_python_shebangs(root_dir: Path):
    """Recursively change #!/usr/bin/pythonX shebangs to #!/usr/bin/env pythonX.

    :param str root_dir: Directory that will be crawled for shebangs.
    """
    file_pattern = re.compile(r"")
    argless_shebang_pattern = re.compile(r"\A#!.*(python\S*)$", re.MULTILINE)
    shebang_pattern_with_args = re.compile(
        r"\A#!.*(python\S*)[ \t\f\v]+(\S+)$", re.MULTILINE
    )

    _replace_in_file(
        root_dir, file_pattern, argless_shebang_pattern, r"#!/usr/bin/env \1"
    )

    # The above rewrite will barf if the shebang includes any args to python.
    # For example, if the shebang was `#!/usr/bin/python3 -Es`, just replacing
    # that with `#!/usr/bin/env python3 -Es` isn't going to work as `env`
    # doesn't support arguments like that.
    #
    # The solution is to replace the shebang with one pointing to /bin/sh, and
    # then exec the original shebang with included arguments. This requires
    # some quoting hacks to ensure the file can be interpreted by both sh as
    # well as python, but it's better than shipping our own `env`.
    _replace_in_file(
        root_dir,
        file_pattern,
        shebang_pattern_with_args,
        r"""#!/bin/sh\n''''exec \1 \2 -- "$0" "$@" # '''""",
    )


def _replace_in_file(
    directory: Path, file_pattern: Pattern, search_pattern: Pattern, replacement: str
) -> None:
    """Search and replaces patterns that match a file pattern.

    :param directory: The directory to look for files.
    :param file_pattern: The file pattern to match inside directory.
    :param search_pattern: A re.compile'd pattern to search for within matching files.
    :param replacement: The string to replace the matching search_pattern with.
    """
    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_pattern.match(file_name):
                file_path = Path(root, file_name)
                # Don't bother trying to rewrite a symlink. It's either invalid
                # or the linked file will be rewritten on its own.
                if not file_path.is_symlink():
                    _search_and_replace_contents(file_path, search_pattern, replacement)


def _search_and_replace_contents(
    file_path: Path, search_pattern: Pattern, replacement: str
) -> None:
    """Search file and replace any occurrence of pattern with replacement.

    :param file_path: Path of file to be searched.
    :param re.RegexObject search_pattern: Pattern for which to search.
    :param replacement: The string to replace pattern.
    """
    try:
        with open(file_path, "r+") as fil:
            try:
                original = fil.read()
            except UnicodeDecodeError:
                # This was probably a binary file. Skip it.
                return

            replaced = search_pattern.sub(replacement, original)
            if replaced != original:
                fil.seek(0)
                fil.truncate()
                fil.write(replaced)
    except PermissionError as err:
        logger.warning("Unable to open %s for writing: %s", file_path, err)
