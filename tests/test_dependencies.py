from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from src.dependencies.loader import DependenciesConfig, DependencySource, load_dependency_graph


class DependencyLoaderTests(unittest.TestCase):
    def test_loads_package_json_and_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            package_json = {
                "dependencies": {"React": "^18.0.0"},
                "devDependencies": {"lodash": "^4.17.0"},
            }
            lockfile = {
                "packages": {
                    "": {},
                    "node_modules/react": {},
                    "node_modules/left-pad": {},
                }
            }
            (root / "package.json").write_text(json.dumps(package_json), encoding="utf-8")
            (root / "package-lock.json").write_text(json.dumps(lockfile), encoding="utf-8")

            config = DependenciesConfig(
                enabled=True,
                sources=[
                    DependencySource(type="manifest", path="package.json"),
                    DependencySource(type="lockfile", path="package-lock.json"),
                ],
                include_transitive=True,
                ecosystems=["npm"],
            )
            graph = load_dependency_graph(config, root, normalize_names=True)

            self.assertIn("react", graph.direct.get("npm", set()))
            self.assertIn("lodash", graph.direct.get("npm", set()))
            self.assertIn("left-pad", graph.transitive.get("npm", set()))

    def test_loads_requirements_and_poetry_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "requirements.txt").write_text(
                "\n".join(["requests==2.31.0", "Django>=4.2", "# comment"]),
                encoding="utf-8",
            )
            (root / "poetry.lock").write_text(
                "\n".join(
                    [
                        "[[package]]",
                        'name = "urllib3"',
                        'version = "2.2.0"',
                    ]
                ),
                encoding="utf-8",
            )

            config = DependenciesConfig(
                enabled=True,
                sources=[
                    DependencySource(type="manifest", path="requirements.txt"),
                    DependencySource(type="lockfile", path="poetry.lock"),
                ],
                include_transitive=True,
                ecosystems=["pip"],
            )
            graph = load_dependency_graph(config, root, normalize_names=True)

            self.assertIn("requests", graph.direct.get("pip", set()))
            self.assertIn("django", graph.direct.get("pip", set()))
            self.assertIn("urllib3", graph.transitive.get("pip", set()))
