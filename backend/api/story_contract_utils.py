"""Helpers for stabilizing legacy story payloads."""

from __future__ import annotations

from typing import Any, Dict

from story.story_asset_service import StoryAssetService


_story_asset_service = StoryAssetService()


def normalize_story_session_init_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy story init payloads into the PR-02 contract shape."""

    payload = dict(result or {})
    payload.setdefault("status", "initialized")
    return payload


def normalize_story_turn_payload(result: Dict[str, Any], *, thread_id: str) -> Dict[str, Any]:
    """Normalize legacy story round payloads into a stable DTO shape."""

    payload = dict(result or {})
    payload["thread_id"] = str(payload.get("thread_id") or thread_id)
    payload["round_no"] = int(payload.get("round_no", 0) or 0)
    payload["player_options"] = list(payload.get("player_options") or [])
    payload["session_restored"] = bool(payload.get("session_restored", False))
    payload["need_reselect_option"] = bool(payload.get("need_reselect_option", False))
    if payload.get("snapshot") is not None:
        payload["snapshot"] = dict(payload.get("snapshot") or {})
    payload = _story_asset_service.merge_story_assets(payload)

    if payload["need_reselect_option"]:
        payload["status"] = "reselect_required"
    elif bool(payload.get("is_game_finished", False)):
        payload["status"] = "completed"
    else:
        payload.setdefault("status", "in_progress")

    return payload
