# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd.
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

import craft_parts
import yaml
from craft_parts import Action, Step


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
