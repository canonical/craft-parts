# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [pytest.mark.plugin]


def test_ninja_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        f"""\
        parts:
          foo:
            plugin: ninja
            source: .
            ninja-target: all
            ninja-build-directory: .
            ninja-install: true
            build-environment:
              - PATH: {new_dir}:${{PATH}}
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("ninja").write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            if [ "${1:-}" = "--version" ]; then
                echo "1.11.1"
                exit 0
            fi
            if [ "${1:-}" = "-C" ]; then
                shift 2
            fi
            if [ "${1:-}" = "all" ]; then
                printf '%s\n' '#include <stdio.h>' 'int main(void) { puts("hello ninja"); return 0; }' > hello.c
                cc hello.c -o hello
                exit 0
            fi
            if [ "${1:-}" = "install" ]; then
                install -D ./hello "${DESTDIR}/usr/bin/hello-ninja"
                exit 0
            fi
            exit 1
            """
        ),
        encoding="utf-8",
    )
    Path("ninja").chmod(0o755)

    lifecycle = LifecycleManager(
        parts,
        application_name="test_ninja_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lifecycle.project_info.prime_dir, "usr", "bin", "hello-ninja")

    output = subprocess.check_output([str(binary)], text=True)
    assert output.strip() == "hello ninja"
