import pathlib
from typing import Literal
from typing_extensions import override
from craft_parts import Action, LifecycleManager, Step, sources
import yaml


class RsyncDirectorySourceModel(sources.BaseSourceModel, frozen=True):
    pattern = "^rsync://"
    source_type: Literal["rsync"] = "rsync"


class RsyncSource(sources.SourceHandler):
    source_model = RsyncDirectorySourceModel

    @override
    def pull(self) -> None:
        self._run(
            [
                "rsync",
                "--archive",
                "--delete",
                self.source,
                self.part_src_dir.as_posix(),
            ]
        )

# docs[register-source:start]
sources.register(RsyncSource)
# docs[register-source:end]

parts_path = pathlib.Path(__file__).parent / "rsync_parts.yaml"
parts = yaml.safe_load(parts_path.read_text())

# docs[run-lifecycle:start]
lcm = LifecycleManager(
    parts,
    application_name="rsync_parts",
    cache_dir=pathlib.Path.home() / ".cache",
)
with lcm.action_executor() as ctx:
    ctx.execute(Action("my-part", Step.PULL))
# docs[run-lifecycle:end]
