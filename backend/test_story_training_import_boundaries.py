"""Static boundary tests for story/training implementation domains.

These tests guard against direct implementation-level imports across domains:
- story/* must not import training/*
- training/* must not import story/*
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import Iterable


BACKEND_ROOT = Path(__file__).resolve().parent
STORY_ROOT = BACKEND_ROOT / "story"
TRAINING_ROOT = BACKEND_ROOT / "training"


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _collect_forbidden_imports(
    *,
    files: Iterable[Path],
    forbidden_domain: str,
) -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    forbidden_prefix = f"{forbidden_domain}."

    for file_path in files:
        module = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for imported in node.names:
                    name = imported.name
                    if name == forbidden_domain or name.startswith(forbidden_prefix):
                        violations.append((file_path, node.lineno, f"import {name}"))

            if isinstance(node, ast.ImportFrom) and node.module:
                module_name = node.module
                if module_name == forbidden_domain or module_name.startswith(forbidden_prefix):
                    imported_names = ", ".join(alias.name for alias in node.names)
                    violations.append(
                        (
                            file_path,
                            node.lineno,
                            f"from {module_name} import {imported_names}",
                        )
                    )

    return violations


def _format_violations(violations: list[tuple[Path, int, str]]) -> str:
    formatted = [
        f"{path.relative_to(BACKEND_ROOT)}:{lineno} -> {statement}"
        for path, lineno, statement in violations
    ]
    return "\n".join(formatted)


class StoryTrainingImportBoundaryTestCase(unittest.TestCase):
    """Lock story/training implementation domains from cross-importing each other."""

    def test_story_domain_should_not_import_training_domain(self):
        violations = _collect_forbidden_imports(
            files=_iter_python_files(STORY_ROOT),
            forbidden_domain="training",
        )

        self.assertEqual(
            violations,
            [],
            msg=(
                "story domain must not import training implementation modules:\n"
                f"{_format_violations(violations)}"
            ),
        )

    def test_training_domain_should_not_import_story_domain(self):
        violations = _collect_forbidden_imports(
            files=_iter_python_files(TRAINING_ROOT),
            forbidden_domain="story",
        )

        self.assertEqual(
            violations,
            [],
            msg=(
                "training domain must not import story implementation modules:\n"
                f"{_format_violations(violations)}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
