"""Story-session domain service."""

from __future__ import annotations

from typing import Any, Dict

from story.exceptions import StorySessionExpiredError, StorySessionNotFoundError
from story.story_asset_service import StoryAssetService
from story.story_session_query_policy import StorySessionQueryPolicy
from story.story_response_utils import attach_snapshot_metadata
from utils.logger import get_logger

logger = get_logger(__name__)


class StorySessionService:
    """Own story-session lifecycle reads and initialization."""

    def __init__(
        self,
        *,
        session_manager,
        story_asset_service: StoryAssetService | None = None,
        session_query_policy: StorySessionQueryPolicy | None = None,
    ):
        self.session_manager = session_manager
        self.story_asset_service = story_asset_service or StoryAssetService()
        self.session_query_policy = session_query_policy or StorySessionQueryPolicy()

    def init_game(
        self,
        *,
        user_id: str | None,
        character_id: int | None,
        game_mode: str,
    ) -> Dict[str, str]:
        logger.info(
            "story session init requested: user_id=%s character_id=%s game_mode=%s",
            user_id,
            character_id,
            game_mode,
        )

        if not character_id:
            raise ValueError("character_id is required")

        session = self.session_manager.create_session(
            user_id=user_id,
            character_id=character_id,
            game_mode=game_mode,
        )
        logger.info("story session created: thread_id=%s", session.thread_id)

        return {
            "thread_id": session.thread_id,
            "user_id": session.user_id,
            "game_mode": session.game_mode,
            "status": "initialized",
        }

    def list_recent_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ) -> Dict[str, Any]:
        authorized_user_id = self.session_query_policy.authorize_recent_sessions_query(
            requested_user_id=user_id,
            actor_user_id=actor_user_id,
        )
        logger.info(
            "story recent sessions requested: user_id=%s actor_user_id=%s policy_mode=%s limit=%s",
            authorized_user_id,
            actor_user_id,
            self.session_query_policy.mode,
            limit,
        )

        sessions = self.session_manager.list_story_sessions(user_id=authorized_user_id, limit=limit)
        latest_snapshots = self.session_manager.get_latest_snapshots(
            [session_record.thread_id for session_record in sessions]
        )
        summaries = []
        for session_record in sessions:
            latest_snapshot = latest_snapshots.get(session_record.thread_id)
            snapshot_summary = latest_snapshot.to_summary() if latest_snapshot is not None else {}
            effective_status = self._resolve_effective_status(session_record)
            summaries.append(
                {
                    "thread_id": session_record.thread_id,
                    "user_id": session_record.user_id,
                    "character_id": int(session_record.character_id),
                    "game_mode": session_record.game_mode,
                    "status": effective_status,
                    "round_no": int(session_record.current_round_no or 0),
                    "scene": snapshot_summary.get("scene") or session_record.current_scene_id,
                    "event_title": snapshot_summary.get("event_title"),
                    "is_initialized": bool(session_record.is_initialized),
                    "has_ending": bool(
                        snapshot_summary.get("is_game_finished", False)
                        or effective_status == "completed"
                    ),
                    "can_resume": effective_status not in {"completed", "expired"},
                    "updated_at": snapshot_summary.get("updated_at")
                    or self._isoformat(getattr(session_record, "updated_at", None)),
                    "expires_at": self._isoformat(getattr(session_record, "expires_at", None)),
                }
            )

        return {
            "user_id": authorized_user_id,
            "sessions": summaries,
        }

    def get_session_snapshot(self, thread_id: str) -> Dict[str, Any]:
        session_record = self.session_manager.get_session_record(thread_id)
        if session_record is None:
            raise StorySessionNotFoundError(thread_id=thread_id)
        if session_record.is_expired():
            self.session_manager.story_store.mark_story_session_expired(thread_id)
            raise StorySessionExpiredError(thread_id=thread_id)

        snapshot_record = self.session_manager.get_latest_snapshot(thread_id)
        if snapshot_record is None:
            response_payload = self._refresh_asset_view(
                session_record=session_record,
                payload={
                    "thread_id": thread_id,
                    "status": session_record.status,
                    "round_no": session_record.current_round_no,
                    "scene": session_record.current_scene_id,
                    "updated_at": (
                        session_record.updated_at.isoformat() if session_record.updated_at else None
                    ),
                    "expires_at": (
                        session_record.expires_at.isoformat() if session_record.expires_at else None
                    ),
                    "snapshot": {
                        "thread_id": thread_id,
                        "status": session_record.status,
                        "round_no": session_record.current_round_no,
                        "scene": session_record.current_scene_id,
                        "event_title": None,
                        "current_states": {},
                        "is_event_finished": False,
                        "is_game_finished": False,
                        "updated_at": session_record.updated_at.isoformat() if session_record.updated_at else None,
                        "expires_at": session_record.expires_at.isoformat() if session_record.expires_at else None,
                    },
                },
            )
            return response_payload

        response_payload = self._refresh_asset_view(
            session_record=session_record,
            payload=dict(snapshot_record.response_payload or {}),
        )
        response_payload["updated_at"] = (
            snapshot_record.updated_at.isoformat() if snapshot_record.updated_at else None
        )
        response_payload["expires_at"] = (
            snapshot_record.expires_at.isoformat() if snapshot_record.expires_at else None
        )
        return attach_snapshot_metadata(
            payload=response_payload,
            round_no=snapshot_record.round_no,
            status=snapshot_record.status,
            snapshot_record=snapshot_record,
            thread_id=thread_id,
        )

    def refresh_story_response_payload(
        self,
        *,
        thread_id: str,
        payload: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """Rebuild a story response view from persisted business facts."""

        session_record = self.session_manager.get_session_record(thread_id)
        if session_record is None:
            raise StorySessionNotFoundError(thread_id=thread_id)
        if session_record.is_expired():
            self.session_manager.story_store.mark_story_session_expired(thread_id)
            raise StorySessionExpiredError(thread_id=thread_id)
        return self._refresh_asset_view(
            session_record=session_record,
            payload=dict(payload or {}),
        )

    def _refresh_asset_view(
        self,
        *,
        session_record,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        refreshed = dict(payload or {})
        scene_id = (
            refreshed.get("scene")
            or getattr(session_record, "current_scene_id", None)
        )
        refreshed["scene"] = scene_id

        stored_assets = dict(refreshed.get("assets") or {})
        stored_scene_asset = dict(stored_assets.get("scene_image") or {})
        stored_composite_asset = dict(stored_assets.get("composite_image") or {})

        resolved_scene_url = self.story_asset_service.resolve_scene_image_url(scene_id)
        resolved_composite_url = self.story_asset_service.find_latest_composite_image_url(
            character_id=int(getattr(session_record, "character_id", 0) or 0),
            scene_id=scene_id,
        )

        refreshed["scene_image_url"] = resolved_scene_url
        refreshed["composite_image_url"] = resolved_composite_url
        refreshed["assets"] = dict(stored_assets)
        if resolved_scene_url:
            refreshed["assets"]["scene_image"] = {
                "type": "scene_image",
                "status": StoryAssetService.READY,
                "url": resolved_scene_url,
            }
        if resolved_composite_url:
            refreshed["assets"]["composite_image"] = {
                "type": "composite_image",
                "status": StoryAssetService.READY,
                "url": resolved_composite_url,
            }

        return self.story_asset_service.merge_story_assets(
            refreshed,
            scene_pending=(
                not refreshed.get("scene_image_url")
                and stored_scene_asset.get("status") == StoryAssetService.PENDING
            ),
            composite_pending=(
                not refreshed.get("composite_image_url")
                and stored_composite_asset.get("status") == StoryAssetService.PENDING
            ),
        )

    @staticmethod
    def _resolve_effective_status(session_record) -> str:
        if session_record is None:
            return "missing"
        if session_record.is_expired():
            return "expired"
        return str(getattr(session_record, "status", "initialized") or "initialized")

    @staticmethod
    def _isoformat(value) -> str | None:
        return value.isoformat() if value is not None else None
