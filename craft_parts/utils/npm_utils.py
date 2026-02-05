from pathlib import Path
import json
from glob import escape
from typing import Any
from semantic_version import NpmSpec, Version


def _get_npm_basename(pkg_name: str) -> str:
    # some scoped packages eg. @comanpy/my-package
    # are packed as company-my-package-version.tgz
    if pkg_name.startswith("@"):
        scope, name = pkg_name[1:].split("/", 1)
        return f"{scope}-{name}"
    return pkg_name


def _find_best_version(available_versions: list[str], dep_version: str):
    spec = NpmSpec(dep_version)
    return str(spec.select([Version(v) for v in available_versions]))


def _find_tarball(cache_dir: Path, dep: str, dep_version: str) -> str:
    if not (existing_tarballs := sorted(cache_dir.glob(f"{escape(dep)}-*.tgz"))):
        raise RuntimeError(
            f"Error: could not resolve dependency '{dep} ({dep_version})`"
        )
    available_versions = [
        tarball.name.removeprefix(f"{dep}-").removesuffix(".tgz")
        for tarball in existing_tarballs
    ]
    if len(available_versions) > 1:
        best_version = _find_best_version(available_versions, dep_version)
        tarball_path = cache_dir / f"{dep}-{best_version}.tgz"
        if not tarball_path.is_file():
            raise RuntimeError(
                f"Error: could not resolve dependency '{dep} ({dep_version})`"
            )
        return str(tarball_path)

    return str(existing_tarballs[0])


def find_tarballs(dependencies: dict[str, str], cache_dir: Path) -> list[str]:
    return [
        _find_tarball(cache_dir, _get_npm_basename(dep), dep_version)
        for dep, dep_version in dependencies.items()
    ]

def read_pkg(pkg_path: Path) -> dict[str, Any]:
    if not pkg_path.exists():
        raise RuntimeError(
            f"Error: could not find 'package.json'."
        )
    with pkg_path.open() as f:
        return json.load(f)

def write_pkg(pkg_path: Path, pkg: dict[str, Any]) -> None:
  with pkg_path.open("w") as f:
      json.dump(pkg, f, indent=2)

# def add_bundled_deps(pkg: dict[str, Any]) -> None:

def get_dependencies(pkg_path: Path):
    if not pkg_path.exists():
        raise RuntimeError(
            f"Error: could not find 'package.json'."
        )
    with pkg_path.open() as f:
        pkg = json.load(f)
    return pkg.get("dependencies", {})
