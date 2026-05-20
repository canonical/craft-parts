# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [pytest.mark.plugin]


def test_pnpm_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: pnpm
            source: .
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("package.json").write_text(
        textwrap.dedent(
            """\
            {
              "name": "pnpm-integration-sample",
              "version": "1.0.0",
              "private": true,
              "scripts": {
                "build": "echo building"
              }
            }
            """
        ),
        encoding="utf-8",
    )
    Path("pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")

    Path("pnpm").write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu

            cmd="$1"
            shift

            if [ "$cmd" = "install" ]; then
                exit 0
            fi

            if [ "$cmd" = "run" ] && [ "${1:-}" = "build" ]; then
                mkdir -p "$CRAFT_PART_INSTALL/bin"
                printf '#!/bin/sh\\necho hello pnpm\\n' > "$CRAFT_PART_INSTALL/bin/hello-pnpm"
                chmod +x "$CRAFT_PART_INSTALL/bin/hello-pnpm"
                exit 0
            fi

            echo "unexpected pnpm invocation: $cmd $*" >&2
            exit 1
            """
        ),
        encoding="utf-8",
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_pnpm_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    artifact = Path(lifecycle.project_info.prime_dir, "bin", "hello-pnpm")

    output = subprocess.check_output([str(artifact)], text=True)
    assert output.strip() == "hello pnpm"
