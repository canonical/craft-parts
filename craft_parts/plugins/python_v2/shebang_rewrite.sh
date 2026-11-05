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
# shellcheck disable=SC2154

# Escape the interpreter path for use as a sed replacement.
escaped_interp=${runtime_interp//\\/\\\\}
escaped_interp=${escaped_interp//&/\\&}
escaped_interp=${escaped_interp//|/\\|}
for script in "${CRAFT_PART_INSTALL}/bin"/*; do
  [[ -f ${script} && ! -L ${script} ]] || continue
  read -r shebang <"${script}" || continue
  if [[ ${shebang} == "#!${PIP_PYTHON}"* ]]; then
    sed -i "1 s|^#!${PIP_PYTHON}[^ ]*\( .\+\)\?$|#!${escaped_interp}\1|" "${script}"
  elif [[ ${shebang} == "#!/bin/sh" ]]; then
    # Possibly pip's polyglot header for long interpreter paths; only
    # rewrite it if the second line executes the pip interpreter.
    if [[ $(sed -n 2p "${script}") == "'''exec' ${PIP_PYTHON} "* ]]; then
      printf '#!%s\n' "${runtime_interp}" >"${script}.tmp"
      tail -n +4 "${script}" >>"${script}.tmp"
      # Preserve the script's original mode instead of clobbering
      cat "${script}.tmp" >"${script}" && rm "${script}.tmp"
    fi
  fi
done
