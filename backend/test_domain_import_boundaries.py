from __future__ import annotations

import ast
from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parent
STORY_DIR = BACKEND_DIR / "story"
TRAINING_DIR = BACKEND_DIR / "training"


def _iter_python_files(root_dir: Path):
    for path in sorted(root_dir.rglob("*.py")):
        if path.name.startswith("test_"):
            continue
        yield path


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


class DomainImportBoundaryTestCase(unittest.TestCase):
    def test_story_domain_should_not_import_training_domain(self):
        violations: list[str] = []
        for source_path in _iter_python_files(STORY_DIR):
            for target in _extract_import_targets(source_path):
                if target == "training" or target.startswith("training."):
                    violations.append(f"{source_path}: {target}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "story domain must not import training domain implementation modules:\n"
                + "\n".join(violations)
            ),
        )

    def test_training_domain_should_not_import_story_domain(self):
        violations: list[str] = []
        for source_path in _iter_python_files(TRAINING_DIR):
            for target in _extract_import_targets(source_path):
                if target == "story" or target.startswith("story."):
                    violations.append(f"{source_path}: {target}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "training domain must not import story domain implementation modules:\n"
                + "\n".join(violations)
            ),
        )


if __name__ == "__main__":
    unittest.main()
