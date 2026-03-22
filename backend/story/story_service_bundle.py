"""Story-domain wiring bundle.

This module owns story service composition so API dependency wiring remains a
thin assembly entrypoint instead of a domain orchestrator.
"""

from __future__ import annotations

from concurrent.futures import Executor
from dataclasses import dataclass

from story.story_session_query_policy import StorySessionQueryPolicy


@dataclass(frozen=True)
class StoryServiceBundle:
    """One shared story-domain wiring bundle."""

    image_executor: Executor
    story_session_query_policy: StorySessionQueryPolicy
    story_asset_service: object
    story_session_service: object
    story_turn_service: object
    story_ending_service: object
    story_history_service: object


def build_story_service_bundle(
    *,
    session_manager,
    image_service,
    character_service,
    image_executor: Executor,
    story_session_query_policy: StorySessionQueryPolicy,
) -> StoryServiceBundle:
    """Compose story services with a single shared collaborator graph."""

    from story.story_asset_service import StoryAssetService
    from story.story_ending_service import StoryEndingService
    from story.story_history_service import StoryHistoryService
    from story.story_session_service import StorySessionService
    from story.story_turn_service import StoryTurnService

    story_asset_service = StoryAssetService(image_service=image_service)
    story_session_service = StorySessionService(
        session_manager=session_manager,
        story_asset_service=story_asset_service,
        session_query_policy=story_session_query_policy,
    )
    story_turn_service = StoryTurnService(
        session_manager=session_manager,
        character_service=character_service,
        story_session_service=story_session_service,
        story_asset_service=story_asset_service,
        image_executor=image_executor,
    )
    story_ending_service = StoryEndingService(
        session_manager=session_manager,
        story_asset_service=story_asset_service,
    )
    story_history_service = StoryHistoryService(
        session_manager=session_manager,
    )
    return StoryServiceBundle(
        image_executor=image_executor,
        story_session_query_policy=story_session_query_policy,
        story_asset_service=story_asset_service,
        story_session_service=story_session_service,
        story_turn_service=story_turn_service,
        story_ending_service=story_ending_service,
        story_history_service=story_history_service,
    )
