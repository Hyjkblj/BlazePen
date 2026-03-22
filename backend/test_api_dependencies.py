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
        dependencies._training_query_service = None
        dependencies._story_image_executor = None
        dependencies._story_session_query_policy = None
        dependencies._story_service_bundle = None

    def test_story_service_bundle_should_share_one_story_contract(self):
        session_manager = object()
        image_service = object()
        character_service = object()
        image_executor = object()
        story_session_query_policy = object()

        story_asset_service = SimpleNamespace(image_service=image_service)
        story_session_service = SimpleNamespace(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
            session_query_policy=story_session_query_policy,
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
            "story.story_session_query_policy.StorySessionQueryPolicy.from_environment",
            return_value=story_session_query_policy,
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
        self.assertIs(bundle.story_session_query_policy, story_session_query_policy)
        self.assertIs(bundle.story_session_service, story_session_service)
        self.assertIs(bundle.story_turn_service, story_turn_service)
        self.assertIs(bundle.story_ending_service, story_ending_service)
        self.assertIs(bundle.story_history_service, story_history_service)
        self.assertIs(bundle.image_executor, image_executor)

        story_asset_cls.assert_called_once_with(image_service=image_service)
        story_session_cls.assert_called_once_with(
            session_manager=session_manager,
            story_asset_service=story_asset_service,
            session_query_policy=story_session_query_policy,
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

        with patch.object(
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
            story_asset_service=story_asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            story_history_service=story_history_service,
        )

    def test_get_training_query_service_should_share_training_runtime_bundle(self):
        training_service = object()
        training_query_service = object()

        with patch(
            "api.services.training_service.TrainingService",
            return_value=training_service,
        ) as training_service_cls, patch(
            "training.training_query_service.TrainingQueryService.from_runtime",
            return_value=training_query_service,
        ) as query_service_factory:
            result = dependencies.get_training_query_service()
            cached_result = dependencies.get_training_query_service()

        self.assertIs(result, training_query_service)
        self.assertIs(cached_result, training_query_service)
        training_service_cls.assert_called_once_with()
        query_service_factory.assert_called_once_with(training_service)


class GameServiceCompositionTestCase(unittest.TestCase):
    def test_game_service_should_require_explicit_story_collaborators(self):
        story_asset_service = SimpleNamespace()
        story_session_service = SimpleNamespace()
        story_turn_service = SimpleNamespace()
        story_ending_service = SimpleNamespace()

        with self.assertRaisesRegex(
            ValueError,
            "story_history_service",
        ):
            GameService(
                story_asset_service=story_asset_service,
                story_session_service=story_session_service,
                story_turn_service=story_turn_service,
                story_ending_service=story_ending_service,
                story_history_service=None,
            )

    def test_game_service_should_keep_legacy_constructor_args_as_compatibility_only(self):
        story_asset_service = SimpleNamespace()
        story_session_service = SimpleNamespace()
        story_turn_service = SimpleNamespace()
        story_ending_service = SimpleNamespace()
        story_history_service = SimpleNamespace()

        service = GameService(
            story_asset_service=story_asset_service,
            story_session_service=story_session_service,
            story_turn_service=story_turn_service,
            story_ending_service=story_ending_service,
            story_history_service=story_history_service,
            character_service=object(),
            image_service=object(),
            session_manager=object(),
            image_executor=object(),
        )

        self.assertIs(service.story_asset_service, story_asset_service)
        self.assertIs(service.story_session_service, story_session_service)
        self.assertIs(service.story_turn_service, story_turn_service)
        self.assertIs(service.story_ending_service, story_ending_service)
        self.assertIs(service.story_history_service, story_history_service)


if __name__ == "__main__":
    unittest.main()
