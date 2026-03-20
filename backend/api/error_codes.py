"""Stable API error codes used by the backend contract layer."""

from __future__ import annotations


VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
NOT_FOUND = "NOT_FOUND"

STORY_SESSION_NOT_FOUND = "STORY_SESSION_NOT_FOUND"
STORY_SESSION_NOT_INITIALIZED = "STORY_SESSION_NOT_INITIALIZED"
STORY_SESSION_EXPIRED = "STORY_SESSION_EXPIRED"
STORY_SESSION_ACCESS_DENIED = "STORY_SESSION_ACCESS_DENIED"
STORY_SESSION_RESTORE_FAILED = "STORY_SESSION_RESTORE_FAILED"
STORY_OPTION_RESELECT_REQUIRED = "STORY_OPTION_RESELECT_REQUIRED"
STORY_ROUND_DUPLICATE = "STORY_ROUND_DUPLICATE"

TRAINING_SESSION_NOT_FOUND = "TRAINING_SESSION_NOT_FOUND"
TRAINING_SESSION_COMPLETED = "TRAINING_SESSION_COMPLETED"
TRAINING_SESSION_RECOVERY_STATE_CORRUPTED = "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED"
TRAINING_ROUND_DUPLICATE = "TRAINING_ROUND_DUPLICATE"

CHARACTER_NOT_FOUND = "CHARACTER_NOT_FOUND"
IMAGE_GENERATION_FAILED = "IMAGE_GENERATION_FAILED"
IMAGE_PROCESSING_FAILED = "IMAGE_PROCESSING_FAILED"
LLM_SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE"
TTS_SERVICE_UNAVAILABLE = "TTS_SERVICE_UNAVAILABLE"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


def infer_story_error_code(message: str, default: str = VALIDATION_ERROR) -> str:
    """Map legacy story-domain error text to a stable error code.

    This is an explicit transitional compatibility layer for historical
    ValueError-based story services. PR-03 should replace this with domain
    exceptions once story persistence lands.
    """

    normalized = (message or "").strip().lower()
    if "not found" in normalized:
        if "expired" in normalized:
            return STORY_SESSION_EXPIRED
        return STORY_SESSION_NOT_FOUND
    if "game not initialized" in normalized:
        return STORY_SESSION_NOT_INITIALIZED
    if "please request options again" in normalized:
        return STORY_OPTION_RESELECT_REQUIRED
    if "duplicate story round submission" in normalized or "duplicate round submission" in normalized:
        return STORY_ROUND_DUPLICATE
    if "会话已过期且无法恢复" in message:
        return STORY_SESSION_RESTORE_FAILED
    return default


def infer_training_error_code(message: str, default: str = VALIDATION_ERROR) -> str:
    """Map legacy training-domain error text to a stable error code."""

    normalized = (message or "").strip().lower()
    if "session not found" in normalized:
        return TRAINING_SESSION_NOT_FOUND
    if "training session already completed" in normalized:
        return TRAINING_SESSION_COMPLETED
    if "training session recovery state corrupted" in normalized:
        return TRAINING_SESSION_RECOVERY_STATE_CORRUPTED
    if "duplicate round submission" in normalized:
        return TRAINING_ROUND_DUPLICATE
    return default
