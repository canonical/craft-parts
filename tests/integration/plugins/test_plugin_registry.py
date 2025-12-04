# Copyright 2021,2024-2025 Canonical Ltd.
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
"""Integration tests for the plugin registry."""

import textwrap

import pytest
import yaml
from craft_parts.errors import InvalidPlugin
from craft_parts.lifecycle_manager import LifecycleManager
from craft_parts.plugins.plugins import PluginGroup, set_plugin_group


@pytest.fixture(autouse=True)
def _reset_plugins():
    yield
    set_plugin_group(PluginGroup.DEFAULT)


def test_minimal_missing_autotools(new_dir, partitions):
    """Test that the minimal plugin set doesn't have an autotools plugin.

    The purpose of this test is to ensure that when we set a plugin group, plugins that
    were previously registered become unavailable in reality.
    """
    parts_yaml = textwrap.dedent(
        """
        parts:
          hello:
            source: .
            plugin: autotools
        """
    )
    parts = yaml.safe_load(parts_yaml)

    set_plugin_group(PluginGroup.MINIMAL)

    with pytest.raises(
        InvalidPlugin, match="Plugin 'autotools' in part 'hello' is not registered."
    ):
        LifecycleManager(
            parts,
            application_name="test_autotools",
            cache_dir=new_dir,
            work_dir=new_dir,
            partitions=partitions,
            parallel_build_count=1,
        )
