# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from craft_parts import LifecycleManager, Step

pytestmark = [pytest.mark.plugin, pytest.mark.java]


def test_sbt_plugin(new_dir, partitions):
    parts_yaml = textwrap.dedent(
        """\
        parts:
          foo:
            plugin: sbt
            source: .
            sbt-task: package
            build-packages: [openjdk-21-jdk]
            stage-packages: [openjdk-21-jdk]
        """
    )
    parts = yaml.safe_load(parts_yaml)

    Path("build.sbt").write_text("// placeholder build file used by integration test\n")

    Path("sbt").write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            mkdir -p target/scala-3.3.1
            cat > Main.java <<'EOF'
            public class Main {
                public static void main(String[] args) {
                    System.out.println("hello sbt");
                }
            }
            EOF
            javac Main.java
            cat > MANIFEST.MF <<'EOF'
            Main-Class: Main
            EOF
            jar cfm target/scala-3.3.1/hello-sbt_3-0.1.0.jar MANIFEST.MF Main.class
            """
        ),
        encoding="utf-8",
    )

    lifecycle = LifecycleManager(
        parts,
        application_name="test_sbt_plugin",
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
            f"{lifecycle.project_info.prime_dir}/jar/hello-sbt_3-0.1.0.jar",
        ],
        text=True,
    )
    assert output.strip() == "hello sbt"
