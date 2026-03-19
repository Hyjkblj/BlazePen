"""Story-domain API contract models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api.schemas import ApiResponse, CheckEndingResponse


class StorySessionInitResponse(BaseModel):
    """Story session init payload."""

    thread_id: str
    user_id: str
    game_mode: str
    status: str = "initialized"


class StoryAssetResourceResponse(BaseModel):
    """Structured story asset metadata."""

    type: str
    status: str
    url: Optional[str] = None
    detail: Optional[str] = None


class StoryAssetsResponse(BaseModel):
    """Story asset bundle shared by story init/turn/snapshot payloads."""

    scene_image: StoryAssetResourceResponse
    composite_image: StoryAssetResourceResponse


class StoryTurnResponse(BaseModel):
    """Story scene payload shared by initialization and round submit."""

    thread_id: Optional[str] = None
    status: str = "in_progress"
    round_no: int = 0
    character_dialogue: Optional[str] = None
    player_options: List[Dict[str, Any]] = Field(default_factory=list)
    story_background: Optional[str] = None
    event_title: Optional[str] = None
    scene: Optional[str] = None
    scene_image_url: Optional[str] = None
    composite_image_url: Optional[str] = None
    assets: Optional[StoryAssetsResponse] = None
    current_states: Optional[Dict[str, Any]] = None
    session_restored: bool = False
    need_reselect_option: bool = False
    restored_from_thread_id: Optional[str] = None
    is_event_finished: bool = False
    is_game_finished: bool = False
    snapshot: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class StorySessionInitApiResponse(ApiResponse):
    """Story session init response envelope."""

    data: Optional[StorySessionInitResponse] = None


class StoryTurnApiResponse(ApiResponse):
    """Story turn response envelope."""

    data: Optional[StoryTurnResponse] = None


class StoryEndingCheckApiResponse(ApiResponse):
    """Story ending check response envelope."""

    data: Optional[CheckEndingResponse] = None


class StorySessionSnapshotResponse(StoryTurnResponse):
    """Story snapshot payload used for refresh and restore flows."""

    updated_at: Optional[str] = None
    expires_at: Optional[str] = None


class StorySessionSnapshotApiResponse(ApiResponse):
    """Story snapshot response envelope."""

    data: Optional[StorySessionSnapshotResponse] = None
