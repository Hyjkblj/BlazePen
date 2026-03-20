from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import api.dependencies as dependencies
from api.services.game_service import GameService


class DependencyWiringTestCase(unittest.TestCase):
    def setUp(self):
        self._reset_dependency_caches()

    def tearDown(self):
        self._reset_dependency_caches()

    def _reset_dependency_caches(self):
        dependencies._game_service = None
        dependencies._character_service = None
        dependencies._image_service = None
        dependencies._tts_service = None
        dependencies._session_manager = None
        dependencies._training_service = None
        dependencies._story_image_executor = None
        dependencies._story_service_bundle = None

    def test_story_service_bundle_should_share_one_story_contract(self):
        session_manager = object()
        image_service = object()
        character_service = object()
        image_executor = object()

        story_asset_service = SimpleNamespace(image_service=image_service)
        story_session_service = SimpleNamespace(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_turn_service = SimpleNamespace(
            session_manager=session_manager,
            character_service=character_service,
            story_session_service=story_session_service,
            story_asset_service=story_asset_service,
            image_executor=image_executor,
        )
        story_ending_service = SimpleNamespace(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_history_service = SimpleNamespace(
            session_manager=session_manager,
        )

        with patch.object(dependencies, "get_session_manager", return_value=session_manager), patch.object(
            dependencies,
            "get_image_service",
            return_value=image_service,
        ), patch.object(
            dependencies,
            "get_character_service",
            return_value=character_service,
        ), patch.object(
            dependencies,
            "get_story_image_executor",
            return_value=image_executor,
        ), patch(
            "story.story_asset_service.StoryAssetService",
            return_value=story_asset_service,
        ) as story_asset_cls, patch(
            "story.story_session_service.StorySessionService",
            return_value=story_session_service,
        ) as story_session_cls, patch(
            "story.story_turn_service.StoryTurnService",
            return_value=story_turn_service,
        ) as story_turn_cls, patch(
            "story.story_ending_service.StoryEndingService",
            return_value=story_ending_service,
        ) as story_ending_cls, patch(
            "story.story_history_service.StoryHistoryService",
            return_value=story_history_service,
        ) as story_history_cls:
            bundle = dependencies.get_story_service_bundle()

        self.assertIs(bundle.story_asset_service, story_asset_service)
        self.assertIs(bundle.story_session_service, story_session_service)
        self.assertIs(bundle.story_turn_service, story_turn_service)
        self.assertIs(bundle.story_ending_service, story_ending_service)
        self.assertIs(bundle.story_history_service, story_history_service)
        self.assertIs(bundle.image_executor, image_executor)

        story_asset_cls.assert_called_once_with(image_service=image_service)
        story_session_cls.assert_called_once_with(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_turn_cls.assert_called_once_with(
            session_manager=session_manager,
            character_service=character_service,
            story_session_service=story_session_service,
            story_asset_service=story_asset_service,
            image_executor=image_executor,
        )
        story_ending_cls.assert_called_once_with(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_history_cls.assert_called_once_with(
            session_manager=session_manager,
        )

    def test_get_game_service_should_inject_shared_story_bundle(self):
        session_manager = object()
        image_service = object()
        character_service = object()
        image_executor = object()

        story_asset_service = object()
        story_session_service = object()
        story_turn_service = object()
        story_ending_service = object()
        story_history_service = object()
        bundle = SimpleNamespace(
            image_executor=image_executor,
            story_asset_service=story_asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            story_history_service=story_history_service,
        )
        game_service = object()

        with patch.object(dependencies, "get_session_manager", return_value=session_manager), patch.object(
            dependencies,
            "get_image_service",
            return_value=image_service,
        ), patch.object(
            dependencies,
            "get_character_service",
            return_value=character_service,
        ), patch.object(
            dependencies,
            "get_story_service_bundle",
            return_value=bundle,
        ), patch(
            "api.services.game_service.GameService",
            return_value=game_service,
        ) as game_service_cls:
            result = dependencies.get_game_service()
            cached_result = dependencies.get_game_service()

        self.assertIs(result, game_service)
        self.assertIs(cached_result, game_service)
        game_service_cls.assert_called_once_with(
            character_service=character_service,
            image_service=image_service,
            session_manager=session_manager,
            story_asset_service=story_asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            story_history_service=story_history_service,
            image_executor=image_executor,
        )


class GameServiceCompositionTestCase(unittest.TestCase):
    def test_game_service_should_reuse_injected_turn_executor(self):
        session_manager = SimpleNamespace()
        image_service = SimpleNamespace()
        character_service = SimpleNamespace()
        image_executor = object()

        story_asset_service = SimpleNamespace(image_service=image_service)
        story_session_service = SimpleNamespace(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_turn_service = SimpleNamespace(
            session_manager=session_manager,
            character_service=character_service,
            story_session_service=story_session_service,
            story_asset_service=story_asset_service,
            image_executor=image_executor,
        )
        story_ending_service = SimpleNamespace(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
        )
        story_history_service = SimpleNamespace(
            session_manager=session_manager,
        )

        with patch("api.services.game_service.ThreadPoolExecutor") as executor_cls:
            service = GameService(
                session_manager=session_manager,
                image_service=image_service,
                character_service=character_service,
                story_asset_service=story_asset_service,
                story_session_service=story_session_service,
                story_turn_service=story_turn_service,
                story_ending_service=story_ending_service,
                story_history_service=story_history_service,
            )

        self.assertIs(service.image_executor, image_executor)
        self.assertIs(service.story_session_service, story_session_service)
        self.assertIs(service.story_turn_service, story_turn_service)
        executor_cls.assert_not_called()

    def test_game_service_should_reject_mixed_story_dependency_injection(self):
        shared_session_manager = SimpleNamespace()
        shared_image_service = SimpleNamespace()
        shared_character_service = SimpleNamespace()
        shared_image_executor = object()

        story_asset_service = SimpleNamespace(image_service=shared_image_service)
        mismatched_session_service = SimpleNamespace(
            session_manager=SimpleNamespace(),
            story_asset_service=story_asset_service,
        )
        story_turn_service = SimpleNamespace(
            session_manager=shared_session_manager,
            character_service=shared_character_service,
            story_session_service=mismatched_session_service,
            story_asset_service=story_asset_service,
            image_executor=shared_image_executor,
        )
        story_ending_service = SimpleNamespace(
            session_manager=shared_session_manager,
            story_asset_service=story_asset_service,
        )
        mismatched_history_service = SimpleNamespace(
            session_manager=SimpleNamespace(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "story_session_service.session_manager",
        ):
            GameService(
                session_manager=shared_session_manager,
                image_service=shared_image_service,
                character_service=shared_character_service,
                story_asset_service=story_asset_service,
                story_session_service=mismatched_session_service,
                story_turn_service=story_turn_service,
                story_ending_service=story_ending_service,
                story_history_service=mismatched_history_service,
                image_executor=shared_image_executor,
            )


if __name__ == "__main__":
    unittest.main()
