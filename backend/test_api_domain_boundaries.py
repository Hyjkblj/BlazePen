from __future__ import annotations

import ast
from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parent


def _resolve_file(relative_path: str) -> Path:
    return BACKEND_DIR / relative_path


def _extract_import_targets(source_path: Path) -> list[str]:
    source_text = source_path.read_text(encoding="utf-8")
    module = ast.parse(source_text, filename=str(source_path))

    targets: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.module:
                targets.append(node.module)
    return targets


def _matches_prefix(target: str, prefix: str) -> bool:
    return target == prefix or target.startswith(f"{prefix}.")


class ApiDomainBoundaryTestCase(unittest.TestCase):
    def test_api_files_should_keep_story_training_import_boundaries(self):
        rules: list[tuple[str, list[str]]] = [
            ("api/routers/game.py", ["training"]),
            ("api/routers/characters.py", ["training"]),
            ("api/story_route_handlers.py", ["training"]),
            ("api/story_contract_utils.py", ["training"]),
            ("api/routers/training.py", ["story"]),
            ("api/services/game_service.py", ["training"]),
            ("api/services/game_session.py", ["training"]),
            ("api/services/training_service.py", ["story"]),
        ]

        violations: list[str] = []
        for relative_path, forbidden_prefixes in rules:
            source_path = _resolve_file(relative_path)
            targets = _extract_import_targets(source_path)
            for target in targets:
                if any(_matches_prefix(target, prefix) for prefix in forbidden_prefixes):
                    violations.append(f"{relative_path}: forbidden import {target}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "api layer should not leak story/training implementation boundaries:\n"
                + "\n".join(violations)
            ),
        )

    def test_story_training_domains_should_not_depend_on_api_layer(self):
        domain_dirs = [
            BACKEND_DIR / "story",
            BACKEND_DIR / "training",
        ]
        violations: list[str] = []
        for domain_dir in domain_dirs:
            for source_path in sorted(domain_dir.rglob("*.py")):
                if source_path.name.startswith("test_"):
                    continue
                for target in _extract_import_targets(source_path):
                    if _matches_prefix(target, "api"):
                        violations.append(f"{source_path}: forbidden import {target}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "story/training domain modules must stay independent from api layer:\n"
                + "\n".join(violations)
            ),
        )


if __name__ == "__main__":
    unittest.main()
