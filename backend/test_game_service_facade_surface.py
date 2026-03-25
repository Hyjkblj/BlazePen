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
            "compatibility_exit_conditions",
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

    def test_game_service_should_define_explicit_exit_conditions_for_split_closeout(self):
        exit_conditions = GameService.compatibility_exit_conditions()

        self.assertEqual(
            exit_conditions["migration_trigger"],
            "story_routers_direct_story_domain_services",
        )

        retain_during_split = set(exit_conditions["retain_during_split"])
        remove_after_router_cutover = set(exit_conditions["remove_after_router_cutover"])

        self.assertTrue(remove_after_router_cutover)
        self.assertTrue(remove_after_router_cutover.issubset(retain_during_split))
        self.assertEqual(
            remove_after_router_cutover,
            {
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
            },
        )


if __name__ == "__main__":
    unittest.main()
