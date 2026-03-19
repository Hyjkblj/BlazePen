"""API exception definitions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.error_codes import (
    CHARACTER_NOT_FOUND,
    CONFIGURATION_ERROR,
    IMAGE_GENERATION_FAILED,
    IMAGE_PROCESSING_FAILED,
    INTERNAL_ERROR,
    LLM_SERVICE_UNAVAILABLE,
    STORY_SESSION_NOT_FOUND,
    TTS_SERVICE_UNAVAILABLE,
)


class ServiceException(Exception):
    """Base service-layer exception with a stable error code."""

    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        *,
        error_code: str = INTERNAL_ERROR,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ImageGenerationException(ServiceException):
    """Image generation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            code=500,
            details=details,
            error_code=IMAGE_GENERATION_FAILED,
        )


class ImageProcessingException(ServiceException):
    """Image processing error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            code=500,
            details=details,
            error_code=IMAGE_PROCESSING_FAILED,
        )


class CharacterNotFoundException(ServiceException):
    """Character missing error."""

    def __init__(self, character_id: int):
        super().__init__(
            f"character not found: {character_id}",
            code=404,
            details={"character_id": character_id},
            error_code=CHARACTER_NOT_FOUND,
        )


class GameSessionNotFoundException(ServiceException):
    """Story session missing error."""

    def __init__(self, thread_id: str):
        super().__init__(
            f"story session not found: {thread_id}",
            code=404,
            details={"thread_id": thread_id},
            error_code=STORY_SESSION_NOT_FOUND,
        )


class LLMServiceException(ServiceException):
    """LLM service error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            code=503,
            details=details,
            error_code=LLM_SERVICE_UNAVAILABLE,
        )


class TTSServiceException(ServiceException):
    """TTS service error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            code=503,
            details=details,
            error_code=TTS_SERVICE_UNAVAILABLE,
        )


class ConfigurationException(ServiceException):
    """Configuration error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            code=500,
            details=details,
            error_code=CONFIGURATION_ERROR,
        )
