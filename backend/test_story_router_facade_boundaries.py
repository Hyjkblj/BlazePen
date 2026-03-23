from __future__ import annotations

import ast
from pathlib import Path
import unittest

from api.services.game_service import GameService


BACKEND_DIR = Path(__file__).resolve().parent

STORY_ROUTER_FILES = (
    BACKEND_DIR / "api" / "routers" / "game.py",
    BACKEND_DIR / "api" / "story_route_handlers.py",
)

FORBIDDEN_GAME_SERVICE_COLLABORATOR_ATTRS = {
    "story_asset_service",
    "story_session_service",
    "story_turn_service",
    "story_ending_service",
    "story_history_service",
}


def _iter_game_service_attribute_accesses(source_path: Path):
    source_text = source_path.read_text(encoding="utf-8")
    module = ast.parse(source_text, filename=str(source_path))

    for node in ast.walk(module):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "game_service":
            yield node.attr


def _iter_game_service_method_calls(source_path: Path):
    source_text = source_path.read_text(encoding="utf-8")
    module = ast.parse(source_text, filename=str(source_path))

    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "game_service":
            yield node.func.attr


class StoryRouterFacadeBoundaryTestCase(unittest.TestCase):
    def test_story_router_files_should_not_access_game_service_internal_collaborators(self):
        violations: list[str] = []

        for source_path in STORY_ROUTER_FILES:
            for attr_name in _iter_game_service_attribute_accesses(source_path):
                if attr_name in FORBIDDEN_GAME_SERVICE_COLLABORATOR_ATTRS:
                    violations.append(f"{source_path.name}: forbidden game_service.{attr_name}")

        self.assertEqual(
            violations,
            [],
            msg=(
                "story routes should only call GameService facade methods and must not "
                "reach into internal collaborators:\n" + "\n".join(violations)
            ),
        )

    def test_story_router_files_should_only_call_game_service_compatibility_methods(self):
        allowed_methods = GameService.compatibility_facade_methods()
        violations: list[str] = []

        for source_path in STORY_ROUTER_FILES:
            for method_name in _iter_game_service_method_calls(source_path):
                if method_name not in allowed_methods:
                    violations.append(
                        f"{source_path.name}: forbidden game_service method call {method_name}"
                    )

        self.assertEqual(
            violations,
            [],
            msg=(
                "story routes may only call GameService compatibility facade methods:\n"
                + "\n".join(violations)
            ),
        )


if __name__ == "__main__":
    unittest.main()
