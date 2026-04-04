"""Dependency guardrails for training backend runtime compatibility."""

from __future__ import annotations

from pathlib import Path
import unittest


def _parse_requirements(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        for marker in ["==", ">=", "<=", "~=", ">", "<"]:
            if marker in line:
                name, spec = line.split(marker, 1)
                package_name = name.strip().lower()
                parsed[package_name] = f"{marker}{spec.strip()}"
                break
        else:
            parsed[line.strip().lower()] = ""
    return parsed


class TrainingDependencyConstraintsTestCase(unittest.TestCase):
    def test_requirements_should_pin_fastapi_stack_with_upper_bounds(self):
        requirements_path = Path(__file__).resolve().parent / "requirements.txt"
        requirements = _parse_requirements(requirements_path)

        self.assertIn("fastapi", requirements)
        self.assertIn("<", requirements["fastapi"])

        self.assertIn("starlette", requirements)
        self.assertIn("<", requirements["starlette"])

        self.assertIn("anyio", requirements)
        self.assertIn("<", requirements["anyio"])

        self.assertIn("pydantic", requirements)
        self.assertIn("<", requirements["pydantic"])


if __name__ == "__main__":
    unittest.main()
