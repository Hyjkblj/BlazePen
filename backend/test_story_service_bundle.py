from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from story.story_service_bundle import StoryServiceBundle, build_story_service_bundle


class StoryServiceBundleTestCase(unittest.TestCase):
    def test_build_story_service_bundle_should_compose_shared_story_contract(self):
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

        with patch(
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
            bundle = build_story_service_bundle(
                session_manager=session_manager,
                image_service=image_service,
                character_service=character_service,
                image_executor=image_executor,
                story_session_query_policy=story_session_query_policy,
            )

        self.assertIsInstance(bundle, StoryServiceBundle)
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


if __name__ == "__main__":
    unittest.main()
