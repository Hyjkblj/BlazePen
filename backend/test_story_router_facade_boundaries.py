from __future__ import annotations

import ast
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parent

STORY_ROUTER_FILES = (
    BACKEND_DIR / "api" / "routers" / "game.py",
    BACKEND_DIR / "api" / "routers" / "characters.py",
    BACKEND_DIR / "api" / "story_route_handlers.py",
)

def _parse_module(source_path: Path) -> ast.Module:
    return ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))


def _iter_import_aliases(source_path: Path):
    module = _parse_module(source_path)
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                yield node.module, alias.name
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield None, alias.name


def _contains_name(source_path: Path, name: str) -> bool:
    module = _parse_module(source_path)
    for node in ast.walk(module):
        if isinstance(node, ast.Name) and node.id == name:
            return True
    return False


def _contains_depends_on(source_path: Path, dependency_name: str) -> bool:
    module = _parse_module(source_path)
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Depends":
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Name) and first_arg.id == dependency_name:
            return True
    return False


class StoryRouterDependencyBoundaryTestCase(unittest.TestCase):
    def test_story_routers_should_not_import_game_service_or_getter(self):
        violations: list[str] = []

        for source_path in STORY_ROUTER_FILES:
            for module, symbol in _iter_import_aliases(source_path):
                if module == "api.services.game_service" and symbol == "GameService":
                    violations.append(f"{source_path.name}: imports GameService")
                if module == "api.dependencies" and symbol == "get_game_service":
                    violations.append(f"{source_path.name}: imports get_game_service")

        self.assertEqual(
            violations,
            [],
            msg=(
                "story routers must not depend on GameService/get_game_service after "
                "router cutover:\n" + "\n".join(violations)
            ),
        )

    def test_story_routers_should_wire_via_story_service_bundle_dependency(self):
        missing_story_bundle_getter: list[str] = []
        missing_story_bundle_type: list[str] = []
        depends_on_legacy_game_service: list[str] = []
        for source_path in STORY_ROUTER_FILES:
            if source_path.name == "story_route_handlers.py":
                if not _contains_name(source_path, "StoryServiceBundle"):
                    missing_story_bundle_type.append(source_path.name)
                continue
            if _contains_depends_on(source_path, "get_game_service"):
                depends_on_legacy_game_service.append(source_path.name)
            if not _contains_name(source_path, "get_story_service_bundle"):
                missing_story_bundle_getter.append(source_path.name)

        self.assertEqual(
            missing_story_bundle_getter,
            [],
            msg=(
                "story routers should resolve domain collaborators via "
                "get_story_service_bundle:\n" + "\n".join(missing_story_bundle_getter)
            ),
        )
        self.assertEqual(
            missing_story_bundle_type,
            [],
            msg=(
                "story route handlers should depend on StoryServiceBundle "
                "instead of GameService:\n" + "\n".join(missing_story_bundle_type)
            ),
        )
        self.assertEqual(
            depends_on_legacy_game_service,
            [],
            msg=(
                "story routers should not wire Depends(get_game_service) after "
                "router cutover:\n" + "\n".join(depends_on_legacy_game_service)
            ),
        )


if __name__ == "__main__":
    unittest.main()
