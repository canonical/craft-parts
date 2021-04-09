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

from pathlib import Path

import pytest
import yaml

from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step


@pytest.mark.usefixtures("new_dir")
class TestStates:
    """Verify states definitions and helpers."""

    @pytest.mark.parametrize("step", list(Step))
    def test_load_missing_state(self, step):
        state = states.load_state(Part("missing", {}), step)
        assert state is None

    def test_load_pull_state(self):
        state_data = {
            "assets": {"stage-packages": ["foo"]},
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
        }
        state_file = Path("parts/foo/state/pull")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_state(Part("foo", {}), Step.PULL)

        assert isinstance(state, states.PullState)
        assert state.marshal() == state_data

    def test_load_build_state(self):
        state_data = {
            "assets": {"build-packages": ["foo"]},
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
        }
        state_file = Path("parts/foo/state/build")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_state(Part("foo", {}), Step.BUILD)

        assert isinstance(state, states.BuildState)
        assert state.marshal() == state_data

    def test_load_stage_state(self):
        state_data = {
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
        }
        state_file = Path("parts/foo/state/stage")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_state(Part("foo", {}), Step.STAGE)

        assert isinstance(state, states.StageState)
        assert state.marshal() == state_data

    def test_load_prime_state(self):
        state_data = {
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
            "dependency-paths": {"c"},
            "primed-stage-packages": {"d"},
        }
        state_file = Path("parts/foo/state/prime")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_state(Part("foo", {}), Step.PRIME)

        assert isinstance(state, states.PrimeState)
        assert state.marshal() == state_data
