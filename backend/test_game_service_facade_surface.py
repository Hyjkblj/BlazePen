from __future__ import annotations

import inspect
import unittest

from api.services.game_service import GameService


def _public_method_names(cls: type) -> set[str]:
    names: set[str] = set()
    for name, member in inspect.getmembers(cls, predicate=callable):
        if name.startswith("_"):
            continue
        if getattr(member, "__qualname__", "").startswith(f"{cls.__name__}."):
            names.add(name)
    return names


class GameServiceFacadeSurfaceTestCase(unittest.TestCase):
    def test_game_service_should_keep_a_fixed_compatibility_facade_surface(self):
        expected = {
            "from_story_service_bundle",
            "compatibility_facade_methods",
            "init_game",
            "initialize_story",
            "submit_story_turn",
            "check_ending",
            "get_story_session_snapshot",
            "list_story_sessions",
            "get_story_history",
            "get_story_ending_summary",
            "trigger_ending",
            "normalize_story_turn_payload",
        }

        self.assertEqual(_public_method_names(GameService), expected)
        self.assertEqual(GameService.compatibility_facade_methods(), expected)


if __name__ == "__main__":
    unittest.main()
