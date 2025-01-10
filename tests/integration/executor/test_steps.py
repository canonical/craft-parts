# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021,2025 Canonical Ltd.
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

import textwrap
from pathlib import Path

from _pytest.tmpdir import tmp_path
import pytest

import craft_parts
import yaml
from craft_parts import Action, Step
from craft_parts import plugins
from craft_parts.plugins.dump_plugin import DumpPlugin


def test_run(tmpdir):
    _parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: dump
            source: {tmpdir}/foo_dir

          bar:
            plugin: dump
            source: {tmpdir}/bar_dir
        """
    )

    parts = yaml.safe_load(_parts_yaml)
    foo_source_dir = Path(tmpdir / "foo_dir")
    foo_source_dir.mkdir(mode=0o755)
    Path(foo_source_dir / "foo.txt").touch()

    bar_source_dir = Path(tmpdir / "bar_dir")
    bar_source_dir.mkdir(mode=0o755)
    Path(bar_source_dir / "bar.txt").touch()

    stage_dir = Path(tmpdir / "stage")
    prime_dir = Path(tmpdir / "prime")

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_steps", cache_dir=tmpdir, work_dir=tmpdir
    )

    with lf.action_executor() as ctx:
        ctx.execute(Action("foo", Step.PULL))
        ctx.execute(Action("foo", Step.BUILD))
        ctx.execute(Action("foo", Step.STAGE))
        assert list(stage_dir.rglob("*")) == [stage_dir / "foo.txt"]

        ctx.execute(Action("bar", Step.PULL))
        ctx.execute(Action("bar", Step.BUILD))
        ctx.execute(Action("bar", Step.STAGE))
        assert sorted(stage_dir.rglob("*")) == [
            stage_dir / "bar.txt",
            stage_dir / "foo.txt",
        ]

        ctx.execute(Action("foo", Step.PRIME))
        assert list(prime_dir.rglob("*")) == [prime_dir / "foo.txt"]

        ctx.execute(Action("bar", Step.PRIME))
        assert sorted(prime_dir.rglob("*")) == [
            prime_dir / "bar.txt",
            prime_dir / "foo.txt",
        ]


class FakeDumpPlugin(DumpPlugin):
    """A fake dump plugin for testing."""

    def get_stage_fileset_entries(self) -> list[str]:
        """Don't stage me, bro!."""
        return ["-dont-stage-me-bro", "-stagefright"]

    def get_prime_fileset_entries(self) -> list[str]:
        """Optimus Prime doesn't like decepticons."""
        return ["-usr/include", "-include"]


@pytest.mark.parametrize(
    ("user_stage", "user_prime", "expected_stage", "expected_prime"),
    [
        pytest.param(
            ["*"],
            ["*"],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("hello"),
                Path("usr"),
            ],
            id="default",
        ),
        pytest.param(
            [],
            [],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("hello"),
                Path("usr"),
            ],
            id="default-but-empty",
        ),
        pytest.param(
            ["stagefright"],
            [],
            [
                Path("stagefright"),
                Path("stagefright/actor"),
            ],
            [
                Path("stagefright"),
                Path("stagefright/actor"),
            ],
            id="stage-stagefright",
        ),
        pytest.param(
            ["stagefright"],
            ["*"],
            [
                Path("stagefright"),
                Path("stagefright/actor"),
            ],
            [
                Path("stagefright"),
                Path("stagefright/actor"),
            ],
            id="prime-stagefright-with-wildcard",
        ),
        pytest.param(
            ["stagefright"],
            ["-stagefright"],
            [
                Path("stagefright"),
                Path("stagefright/actor"),
            ],
            [],
            id="stage-but-dont-prime-stagefright",
        ),
        pytest.param(["-*"],[],[],[],id="stage_nothing"),
        pytest.param(
            [],
            ["-*"],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [],
            id="prime-nothing"
        ),
        pytest.param(
            ["*"],
            ["*", "include"],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
            ],
            id="prime-top-level-include",
        ),
        pytest.param(
            ["**"],
            ["*"],
            [
                Path("dont-stage-me-bro"),
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("stagefright"),
                Path("stagefright/actor"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("dont-stage-me-bro"),
                Path("hello"),
                Path("stagefright"),
                Path("stagefright/actor"),
                Path("usr"),
            ],
            id="stage-ignore-excludes",
        ),
        pytest.param(
            ["*"],
            ["**"],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            id="prime-ignore-excludes",
        ),
        pytest.param(
            ["**"],
            ["**"],
            [
                Path("dont-stage-me-bro"),
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("stagefright"),
                Path("stagefright/actor"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            [
                Path("dont-stage-me-bro"),
                Path("hello"),
                Path("include"),
                Path("include/my_cool_user_thing.h"),
                Path("stagefright"),
                Path("stagefright/actor"),
                Path("usr"),
                Path("usr/include"),
                Path("usr/include/my_cool_system_thing.h"),
            ],
            id="ignore-excludes-in-both-stage-and-prime",
        ),
    ]
)
def test_stage_and_prime_with_plugin_customisation(
    new_path, user_stage, user_prime, expected_stage, expected_prime
):
    parts = {
        "parts": {
            "foo": {
                "plugin": "dump",
                "source": "./project",
                "stage": user_stage,
                "prime": user_prime,
            }
        }
    }
    source_path = new_path / "project"
    source_path.mkdir()
    stage_path = new_path / "stage"
    prime_path = new_path / "prime"
    (source_path / "stagefright").mkdir()
    (source_path / "stagefright/actor").touch()
    (source_path / "dont-stage-me-bro").touch()
    (source_path / "usr/include").mkdir(parents=True)
    (source_path / "usr/include/my_cool_system_thing.h").touch()
    (source_path / "include").mkdir()
    (source_path / "include/my_cool_user_thing.h").touch()
    (source_path / "hello").touch()

    plugins.register({"dump": FakeDumpPlugin})

    lf = craft_parts.LifecycleManager(
        parts, application_name="test_plugin_stage_and_prime", cache_dir=new_path / "cache", work_dir=new_path
    )

    with lf.action_executor() as ctx:
        ctx.execute(lf.plan(Step.PRIME))

    actual_stage = sorted(path.relative_to(stage_path) for path in stage_path.rglob("*"))
    actual_prime = sorted(path.relative_to(prime_path) for path in prime_path.rglob("*"))
    assert actual_stage == expected_stage
    assert actual_prime == expected_prime
