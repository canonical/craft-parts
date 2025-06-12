# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021-2025 Canonical Ltd.
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

from pathlib import Path

import pytest
import yaml
from craft_parts.parts import Part
from craft_parts.state_manager import states
from craft_parts.steps import Step


@pytest.mark.usefixtures("new_dir")
class TestStepStates:
    """Verify step state definitions and helpers."""

    @pytest.mark.parametrize("step", list(Step))
    def test_load_missing_state(self, step):
        state = states.load_step_state(Part("missing", {}), step)
        assert state is None

    def test_load_pull_state(self):
        state_data = {
            "assets": {"stage-packages": ["foo"]},
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
            "outdated-files": ["a"],
            "outdated-dirs": ["b"],
            "partitions-contents": {"default": {"files": {"c"}, "directories": {"d"}}},
        }
        state_file = Path("parts/foo/state/pull")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_step_state(Part("foo", {}), Step.PULL)

        assert isinstance(state, states.PullState)
        assert state.marshal() == state_data

    def test_load_build_state(self):
        state_data = {
            "assets": {"build-packages": ["foo"]},
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
            "overlay-hash": "6f7665726c61792d68617368",
            "partitions-contents": {"default": {"files": {"c"}, "directories": {"d"}}},
        }
        state_file = Path("parts/foo/state/build")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_step_state(Part("foo", {}), Step.BUILD)

        assert isinstance(state, states.BuildState)
        assert state.marshal() == state_data

    def test_load_stage_state(self):
        state_data = {
            "part-properties": {"plugin": "nil"},
            "project-options": {"target_arch": "amd64"},
            "files": {"a"},
            "directories": {"b"},
            "overlay-hash": "6f7665726c61792d68617368",
            "backstage-directories": {"*"},
            "backstage-files": set(),
            "partitions-contents": {"default": {"files": {"c"}, "directories": {"d"}}},
        }
        state_file = Path("parts/foo/state/stage")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_step_state(Part("foo", {}), Step.STAGE)

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
            "partitions-contents": {"default": {"files": {"c"}, "directories": {"d"}}},
        }
        state_file = Path("parts/foo/state/prime")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_step_state(Part("foo", {}), Step.PRIME)

        assert isinstance(state, states.PrimeState)
        assert state.marshal() == state_data

    @pytest.mark.parametrize("step", list(Step))
    def test_remove_state(self, step):
        p1 = Part("p1", {})
        state_file = Path("parts/p1/state", step.name.lower())

        Path("parts/p1/state").mkdir(parents=True)
        state_file.touch()

        assert state_file.exists()

        states.remove(p1, step)
        assert state_file.exists() is False


@pytest.mark.usefixtures("new_dir")
class TestMigrationStates:
    """Verify migration state helpers."""

    @pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
    def test_load_overlay_migration_state(self, step):
        state_data = {
            "files": {"a", "b", "c"},
            "directories": {"d", "e", "f"},
            "partitions_contents": {
                "foo": {
                    "files": {"g", "h"},
                    "directories": {"i", "j"},
                }
            },
        }
        state_file = states.get_overlay_migration_state_path(Path("overlay"), step)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(yaml.dump(state_data))

        state = states.load_overlay_migration_state(Path("overlay"), step)
        assert state is not None
        assert state.marshal() == state_data

    @pytest.mark.parametrize("step", [Step.STAGE, Step.PRIME])
    def test_load_migration_state_missing(self, step):
        state = states.load_overlay_migration_state(Path(), step)
        assert state is None

    @pytest.mark.parametrize("step", set(Step) - {Step.STAGE, Step.PRIME})
    def test_load_migration_state_invalid_step(self, step):
        with pytest.raises(RuntimeError) as err:
            states.load_overlay_migration_state(Path(), step)
        assert str(err.value) == f"no overlay migration state in step {step!r}"
