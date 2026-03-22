from __future__ import annotations

import ast
from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parent


def _iter_runner_files(pattern: str):
    for path in sorted(BACKEND_DIR.glob(pattern)):
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


def _matches_prefix(target: str, prefix: str) -> bool:
    return target == prefix or target.startswith(f"{prefix}.")


class RunnerImportBoundaryTestCase(unittest.TestCase):
    def test_story_runner_scripts_should_not_import_training_runner_impl_modules(self):
        forbidden_prefixes = [
            "training_runner_bootstrap",
            "run_training_cli",
            "run_training_service_cli",
            "run_training_service_local",
            "training",
        ]

        violations: list[str] = []
        for source_path in _iter_runner_files("run_story*.py"):
            for target in _extract_import_targets(source_path):
                if any(_matches_prefix(target, prefix) for prefix in forbidden_prefixes):
                    violations.append(f"{source_path.name}: forbidden import {target}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "story runner scripts must not import training runner implementation modules:\n"
                + "\n".join(violations)
            ),
        )

    def test_story_cli_should_depend_on_neutral_bootstrap_module(self):
        """Story operational CLI must use one DB bootstrap source."""

        source_path = BACKEND_DIR / "run_story_cli.py"
        targets = _extract_import_targets(source_path)

        self.assertTrue(
            any(_matches_prefix(target, "backend_runner_bootstrap") for target in targets),
            msg="run_story_cli.py should use backend_runner_bootstrap as single DB bootstrap source",
        )


if __name__ == "__main__":
    unittest.main()
