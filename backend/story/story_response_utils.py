"""Shared story-response helpers."""

from __future__ import annotations

from typing import Any, Dict


def states_to_payload(states: Any) -> Dict[str, Any] | None:
    """Normalize state objects into a stable dict payload."""

    if not states:
        return None
    return {
        "favorability": states.favorability,
        "trust": states.trust,
        "hostility": states.hostility,
        "dependence": states.dependence,
        "emotion": states.emotion,
        "stress": states.stress,
        "anxiety": states.anxiety,
        "happiness": states.happiness,
        "sadness": states.sadness,
        "confidence": states.confidence,
        "initiative": states.initiative,
        "caution": states.caution,
    }


def attach_snapshot_metadata(
    *,
    payload: Dict[str, Any],
    round_no: int,
    status: str,
    snapshot_record,
    thread_id: str,
) -> Dict[str, Any]:
    """Attach stable story-session metadata onto a response payload."""

    enriched = dict(payload or {})
    enriched["thread_id"] = thread_id
    enriched["round_no"] = int(round_no)
    enriched["status"] = status
    if snapshot_record is not None:
        enriched["snapshot"] = snapshot_record.to_summary()
    return enriched


def build_duplicate_story_round_response(
    *,
    session_manager,
    thread_id: str,
    round_no: int,
) -> Dict[str, Any] | None:
    """Read an already-persisted round response for idempotent replay."""

    round_record = session_manager.get_story_round(thread_id, round_no)
    if round_record is None:
        return None
    snapshot_record = session_manager.get_latest_snapshot(thread_id)
    return attach_snapshot_metadata(
        payload=round_record.response_payload,
        round_no=round_record.round_no,
        status=round_record.status,
        snapshot_record=snapshot_record,
        thread_id=thread_id,
    )
