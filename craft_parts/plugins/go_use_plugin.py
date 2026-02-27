# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021,2024 Canonical Ltd.
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

"""The Go Use plugin."""

from pathlib import Path
from typing import Literal

from typing_extensions import override

from .base import Plugin
from .go_plugin import GoPluginEnvironmentValidator
from .properties import PluginProperties

# awk program that comments out replace directives pointing to local directories
# (i.e. where the right-hand side starts with ./ or ../).  It handles both
# single-line replaces and multi-line replace() blocks.
_REMOVE_LOCAL_REPLACES_AWK = r"""
# Returns 1 if `spec` is a replace directive pointing to a local path (./ or ../).
# Matches: <module> [<version>] => ./path  or  <module> [<version>] => ../path
function is_local_replace(spec) {
    return spec ~ /^[[:space:]]*[^[:space:]]+([ \t]+[^[:space:]]+)?[ \t]+=>[ \t]+\.\.?\//
}

BEGIN { inside = 0 }

# Detect the start of a multi-line replace block: replace (
/^[[:space:]]*replace[[:space:]]*\(/ { inside = 1; print; next }

# Detect the closing ) of a replace block
inside && /^[[:space:]]*\)[[:space:]]*$/ { inside = 0; print; next }

# Inside a block: comment out any entry pointing to a local path (./ or ../)
inside {
    stripped = $0; gsub(/^[[:space:]]+/, "", stripped)
    if (is_local_replace(stripped)) { print "// " stripped } else { print }
    next
}

# Single-line replace: replace module => ./path
/^[[:space:]]*replace[[:space:]]/ && /=>/ {
    stripped = $0; gsub(/^[[:space:]]+/, "", stripped)
    spec = substr(stripped, 9)  # strip the leading "replace " (8 chars)
    if (is_local_replace(spec)) { print "// " stripped; next }
}

# Default: print the line unchanged
{ print }
""".strip()


def _remove_local_replaces_cmd(go_mod_path: Path) -> str:
    """Return a bash command that comments out local replace directives in go.mod."""
    return (
        f"awk '{_REMOVE_LOCAL_REPLACES_AWK}'"
        f" '{go_mod_path}' > '{go_mod_path}.tmp'"
        f" && mv '{go_mod_path}.tmp' '{go_mod_path}'"
    )


class GoUsePluginProperties(PluginProperties, frozen=True):
    """The part properties used by the Go Use plugin."""

    plugin: Literal["go-use"] = "go-use"

    # part properties required by the plugin
    source: str  # pyright: ignore[reportGeneralTypeIssues]


class GoUsePlugin(Plugin):
    """A plugin to setup the source into a go workspace.

    The go plugin requires a go compiler installed on your system. This can
    be achieved by adding the appropriate golang package to ``build-packages``,
    or to have it installed or built in a different part. In this case, the
    name of the part supplying the go compiler must be "go".
    """

    properties_class = GoUsePluginProperties
    validator_class = GoPluginEnvironmentValidator

    @classmethod
    def get_out_of_source_build(cls) -> bool:
        """Return whether the plugin performs out-of-source-tree builds."""
        return True

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build environment."""
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build step."""
        return {}

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        dest_dir = (
            self._part_info.part_export_dir / "go-use" / self._part_info.part_name
        )
        go_mod_path = self._part_info.part_src_subdir / "go.mod"

        return [
            _remove_local_replaces_cmd(go_mod_path),
            f"mkdir -p '{dest_dir.parent}'",
            f"ln -sf '{self._part_info.part_src_subdir}' '{dest_dir}'",
        ]
