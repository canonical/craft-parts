#!/bin/bash
# -*- Mode:sh; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2025 Canonical Ltd.
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

# The caller (the Python v2 plugin) prepends the assignment of runtime_interp
# to this script, so shellcheck can't see where it's set.
# shellcheck disable=SC2154,SC2269
runtime_interp=${runtime_interp}

# Rewrite via a temp file and write-through, which handles any character in the
# interpreter path without escaping. Writing through preserves the file's mode.
rewrite_shebang() {
  local script=$1 body_start=$2 args=${3:-}
  printf '#!%s%s\n' "${runtime_interp}" "${args}" >"${script}.tmp"
  tail -n "+${body_start}" "${script}" >>"${script}.tmp"
  cat "${script}.tmp" >"${script}" && rm "${script}.tmp"
}

for script in "${CRAFT_PART_INSTALL}/bin"/*; do
  [[ -f ${script} && ! -L ${script} ]] || continue
  # Read the whole first line (no word splitting): a space in the interpreter
  # path is legal and must not be mistaken for arguments.
  IFS='' read -r shebang <"${script}" || continue
  if [[ ${shebang} == "#!${PIP_PYTHON}"* ]]; then
    # Keep any interpreter arguments after the interpreter path.
    rewrite_shebang "${script}" 2 "${shebang#"#!${PIP_PYTHON}"}"
  elif [[ ${shebang} == "#!/bin/sh" ]]; then
    # Possibly pip's polyglot header for long interpreter paths; only
    # rewrite it if the second line executes the pip interpreter.
    if [[ $(sed -n 2p "${script}") == "'''exec' ${PIP_PYTHON} "* ]]; then
      rewrite_shebang "${script}" 4
    fi
  fi
done
