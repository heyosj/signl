from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .normalize import normalize_package_name
from .types import DependencyGraph


@dataclass
class DependencySource:
    type: str
    path: str


@dataclass
class DependenciesConfig:
    enabled: bool
    sources: list[DependencySource]
    include_transitive: bool
    ecosystems: list[str]


_REQ_SPLIT = re.compile(r"[<>=!~]")


def load_dependency_graph(
    config: DependenciesConfig,
    base_dir: Path,
    normalize_names: bool = True,
) -> DependencyGraph:
    graph = DependencyGraph()
    if not config.enabled:
        return graph

    allowed_ecosystems = {eco.lower() for eco in config.ecosystems} if config.ecosystems else None
    for source in config.sources:
        path = (base_dir / source.path).expanduser()
        if not path.exists():
            continue
        source_type = source.type.lower()
        if source_type == "manifest":
            _load_manifest(path, graph, allowed_ecosystems, normalize_names)
        elif source_type == "lockfile":
            _load_lockfile(path, graph, allowed_ecosystems, normalize_names, config.include_transitive)

    return graph


def _load_manifest(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
) -> None:
    if path.name == "package.json":
        _load_package_json(path, graph, allowed_ecosystems, normalize_names)
    elif path.name.endswith(".txt"):
        _load_requirements(path, graph, allowed_ecosystems, normalize_names)


def _load_lockfile(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
    include_transitive: bool,
) -> None:
    if not include_transitive:
        return
    if path.name == "package-lock.json":
        _load_package_lock(path, graph, allowed_ecosystems, normalize_names)
    elif path.name == "poetry.lock":
        _load_poetry_lock(path, graph, allowed_ecosystems, normalize_names)


def _load_package_json(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
) -> None:
    if allowed_ecosystems and "npm" not in allowed_ecosystems:
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    dependencies = _extract_package_names(data.get("dependencies")) | _extract_package_names(
        data.get("devDependencies")
    )
    normalized = {normalize_package_name(name, "npm", normalize_names) for name in dependencies}
    graph.add_direct("npm", normalized)


def _load_package_lock(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
) -> None:
    if allowed_ecosystems and "npm" not in allowed_ecosystems:
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    packages: set[str] = set()
    if isinstance(data.get("packages"), dict):
        for name in data["packages"].keys():
            if not name:
                continue
            if name.startswith("node_modules/"):
                name = name.split("node_modules/", 1)[1]
            packages.add(name)
    elif isinstance(data.get("dependencies"), dict):
        packages |= _extract_npm_dependencies(data["dependencies"])
    normalized = {normalize_package_name(name, "npm", normalize_names) for name in packages}
    graph.add_transitive("npm", normalized)


def _load_requirements(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
) -> None:
    if allowed_ecosystems and "pip" not in allowed_ecosystems:
        return
    packages: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("-"):
            continue
        name = _REQ_SPLIT.split(cleaned, 1)[0]
        name = name.split("[", 1)[0]
        if name:
            packages.add(name.strip())
    normalized = {normalize_package_name(name, "pip", normalize_names) for name in packages}
    graph.add_direct("pip", normalized)


def _load_poetry_lock(
    path: Path,
    graph: DependencyGraph,
    allowed_ecosystems: set[str] | None,
    normalize_names: bool,
) -> None:
    if allowed_ecosystems and "pip" not in allowed_ecosystems:
        return
    packages: set[str] = set()
    current: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if cleaned == "[[package]]":
            if current.get("name"):
                packages.add(current["name"])
            current = {}
            continue
        if cleaned.startswith("name ="):
            name = cleaned.split("=", 1)[1].strip().strip('"')
            current["name"] = name
    if current.get("name"):
        packages.add(current["name"])
    normalized = {normalize_package_name(name, "pip", normalize_names) for name in packages}
    graph.add_transitive("pip", normalized)


def _extract_package_names(data: Any) -> set[str]:
    if not isinstance(data, dict):
        return set()
    return {str(name) for name in data.keys()}


def _extract_npm_dependencies(data: dict[str, Any]) -> set[str]:
    packages: set[str] = set()
    for name, metadata in data.items():
        packages.add(str(name))
        deps = metadata.get("dependencies")
        if isinstance(deps, dict):
            packages |= _extract_npm_dependencies(deps)
    return packages
