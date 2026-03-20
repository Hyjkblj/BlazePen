"""Helpers for stabilizing legacy story payloads."""

from __future__ import annotations

from typing import Any, Dict

from story.story_asset_service import StoryAssetService


def normalize_story_session_init_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy story init payloads into the PR-02 contract shape."""

    payload = dict(result or {})
    payload.setdefault("status", "initialized")
    return payload


def normalize_story_turn_payload(
    result: Dict[str, Any],
    *,
    thread_id: str,
    story_asset_service: StoryAssetService,
) -> Dict[str, Any]:
    """Normalize legacy story round payloads into a stable DTO shape."""

    payload = dict(result or {})
    payload["thread_id"] = str(payload.get("thread_id") or thread_id)
    payload["round_no"] = int(payload.get("round_no", 0) or 0)
    payload["player_options"] = list(payload.get("player_options") or [])
    payload["session_restored"] = bool(payload.get("session_restored", False))
    payload["need_reselect_option"] = bool(payload.get("need_reselect_option", False))
    if payload.get("snapshot") is not None:
        payload["snapshot"] = dict(payload.get("snapshot") or {})
    payload = story_asset_service.merge_story_assets(payload)

    if payload["need_reselect_option"]:
        payload["status"] = "reselect_required"
    elif bool(payload.get("is_game_finished", False)):
        payload["status"] = "completed"
    else:
        payload.setdefault("status", "in_progress")

    return payload


def normalize_story_session_list_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize recent session summaries into a stable DTO shape."""

    payload = dict(result or {})
    sessions = []
    for item in list(payload.get("sessions") or []):
        normalized = dict(item or {})
        normalized["character_id"] = int(normalized.get("character_id", 0) or 0)
        normalized["round_no"] = int(normalized.get("round_no", 0) or 0)
        normalized["is_initialized"] = bool(normalized.get("is_initialized", False))
        normalized["has_ending"] = bool(normalized.get("has_ending", False))
        normalized["can_resume"] = bool(normalized.get("can_resume", False))
        normalized.setdefault("status", "initialized")
        sessions.append(normalized)
    payload["sessions"] = sessions
    return payload


def normalize_story_history_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize persisted story history into a stable DTO shape."""

    payload = dict(result or {})
    payload["current_round_no"] = int(payload.get("current_round_no", 0) or 0)
    normalized_history = []
    for item in list(payload.get("history") or []):
        normalized_item = dict(item or {})
        normalized_item["round_no"] = int(normalized_item.get("round_no", 0) or 0)
        normalized_item.setdefault("status", "in_progress")
        normalized_item["user_action"] = dict(normalized_item.get("user_action") or {})
        normalized_item["state_summary"] = dict(normalized_item.get("state_summary") or {})
        normalized_item["state_summary"]["changes"] = dict(
            normalized_item["state_summary"].get("changes") or {}
        )
        normalized_item["state_summary"]["current_states"] = dict(
            normalized_item["state_summary"].get("current_states") or {}
        )
        normalized_item["is_event_finished"] = bool(
            normalized_item.get("is_event_finished", False)
        )
        normalized_item["is_game_finished"] = bool(
            normalized_item.get("is_game_finished", False)
        )
        normalized_history.append(normalized_item)
    payload["history"] = normalized_history
    return payload


def normalize_story_ending_summary_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize story ending summary into a stable DTO shape."""

    payload = dict(result or {})
    payload["round_no"] = int(payload.get("round_no", 0) or 0)
    payload["has_ending"] = bool(payload.get("has_ending", False))
    if payload.get("ending") is not None:
        ending = dict(payload.get("ending") or {})
        ending["key_states"] = dict(ending.get("key_states") or {})
        payload["ending"] = ending
    return payload
