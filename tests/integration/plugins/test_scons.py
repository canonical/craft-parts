import subprocess
import textwrap
from pathlib import Path

import yaml
from craft_parts import LifecycleManager, Step


def test_scons_plugin(new_dir, partitions):
    """Test builds with the scons plugin"""
    source_location = Path(__file__).parent / "test_scons"

    parts_yaml = textwrap.dedent(
        f"""
        parts:
          foo:
            plugin: scons
            source: {source_location}
            scons-parameters:
              - greeting=Hello
              - person-name=craft-parts
        """
    )
    parts = yaml.safe_load(parts_yaml)
    lf = LifecycleManager(
        parts,
        application_name="test_scons",
        cache_dir=new_dir,
        work_dir=new_dir,
        partitions=partitions,
    )
    actions = lf.plan(Step.PRIME)

    with lf.action_executor() as ctx:
        ctx.execute(actions)

    binary = Path(lf.project_info.prime_dir, "bin", "hello")
    assert binary.is_file()

    output = subprocess.check_output([str(binary)], text=True)
    # The output "Hello, craft-parts!" verifies that the scons-parameters were forwarded correctly.
    assert output == "Hello, craft-parts!\n"
