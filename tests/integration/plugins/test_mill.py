# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [pytest.mark.plugin, pytest.mark.java]


def test_mill_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: mill
            source: .
            mill-task: foo.assembly
            build-packages: [openjdk-21-jdk]
            stage-packages: [openjdk-21-jdk]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("build.sc").write_text("// build file used by integration test\n")

    Path("mill").write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            mkdir -p out/foo/assembly.dest
            cat > Main.java <<'EOF'
            public class Main {
                public static void main(String[] args) {
                    System.out.println("hello mill");
                }
            }
            EOF
            javac Main.java
            cat > MANIFEST.MF <<'EOF'
            Main-Class: Main
            EOF
            jar cfm out/foo/assembly.dest/hello-mill.jar MANIFEST.MF Main.class
            """
        ),
        encoding="utf-8",
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_mill_plugin",
        cache_dir=new_dir,
        partitions=partitions,
    )
    actions = lifecycle.plan(Step.PRIME)

    with lifecycle.action_executor() as ctx:
        ctx.execute(actions)

    java_binary = Path(lifecycle.project_info.prime_dir, "bin", "java")
    assert java_binary.is_file()

    output = subprocess.check_output(
        [
            str(java_binary),
            "-jar",
            f"{lifecycle.project_info.prime_dir}/jar/hello-mill.jar",
        ],
        text=True,
    )
    assert output.strip() == "hello mill"
