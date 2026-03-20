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


class StorySessionSummaryResponse(BaseModel):
    """Recent story session summary used by restore entry flows."""

    thread_id: str
    user_id: str
    character_id: int
    game_mode: str = "solo"
    status: str = "initialized"
    round_no: int = 0
    scene: Optional[str] = None
    event_title: Optional[str] = None
    is_initialized: bool = False
    has_ending: bool = False
    can_resume: bool = False
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None


class StorySessionListResponse(BaseModel):
    """Story session list response."""

    user_id: str
    sessions: List[StorySessionSummaryResponse] = Field(default_factory=list)


class StorySessionListApiResponse(ApiResponse):
    """Story session list response envelope."""

    data: Optional[StorySessionListResponse] = None


class StoryHistoryUserActionResponse(BaseModel):
    """Structured user action summary for a persisted story round."""

    kind: str = "free_text"
    summary: str = ""
    raw_input: Optional[str] = None
    option_index: Optional[int] = None
    option_text: Optional[str] = None
    option_type: Optional[str] = None


class StoryHistoryStateSummaryResponse(BaseModel):
    """State change summary for a persisted story round."""

    changes: Dict[str, float] = Field(default_factory=dict)
    current_states: Dict[str, float] = Field(default_factory=dict)


class StoryHistoryItemResponse(BaseModel):
    """Product-facing story history item."""

    round_no: int
    status: str = "in_progress"
    scene: Optional[str] = None
    event_title: Optional[str] = None
    character_dialogue: Optional[str] = None
    user_action: StoryHistoryUserActionResponse
    state_summary: StoryHistoryStateSummaryResponse = Field(
        default_factory=StoryHistoryStateSummaryResponse
    )
    is_event_finished: bool = False
    is_game_finished: bool = False
    created_at: Optional[str] = None


class StorySessionHistoryResponse(BaseModel):
    """Persisted story history response."""

    thread_id: str
    status: str = "initialized"
    current_round_no: int = 0
    latest_scene: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    latest_snapshot: Optional[Dict[str, Any]] = None
    history: List[StoryHistoryItemResponse] = Field(default_factory=list)


class StorySessionHistoryApiResponse(ApiResponse):
    """Story history response envelope."""

    data: Optional[StorySessionHistoryResponse] = None


class StoryEndingKeyStatesResponse(BaseModel):
    """Key state summary exposed by the ending DTO."""

    favorability: Optional[float] = None
    trust: Optional[float] = None
    hostility: Optional[float] = None
    dependence: Optional[float] = None


class StoryEndingSummaryItemResponse(BaseModel):
    """Product-facing ending summary payload."""

    type: str
    description: str
    scene: Optional[str] = None
    event_title: Optional[str] = None
    key_states: StoryEndingKeyStatesResponse = Field(
        default_factory=StoryEndingKeyStatesResponse
    )


class StoryEndingSummaryResponse(BaseModel):
    """Read-only story ending summary response."""

    thread_id: str
    status: str = "initialized"
    round_no: int = 0
    has_ending: bool = False
    ending: Optional[StoryEndingSummaryItemResponse] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None


class StoryEndingSummaryApiResponse(ApiResponse):
    """Story ending summary response envelope."""

    data: Optional[StoryEndingSummaryResponse] = None
