"""数据库模型与可选模型服务导出。

这里优先导出轻量级 ORM 模型，
大模型服务类改为按需延迟导入，避免训练域导入模型时被重依赖拖慢或拖挂。
"""

from __future__ import annotations

from .character import Character, CharacterAttribute, CharacterState
from .training import (
    EndingResult,
    KtObservation,
    KtStateSnapshot,
    NarrativeStateSnapshot,
    RoundEvaluation,
    ScenarioRecommendationLog,
    TrainingAuditEvent,
    TrainingRound,
    TrainingSession,
)

__all__ = [
    "Character",
    "CharacterAttribute",
    "CharacterState",
    "TrainingSession",
    "TrainingRound",
    "RoundEvaluation",
    "KtStateSnapshot",
    "KtObservation",
    "NarrativeStateSnapshot",
    "EndingResult",
    "ScenarioRecommendationLog",
    "TrainingAuditEvent",
    "TextModelService",
    "ImageModelService",
    "VoiceModelService",
]


def __getattr__(name: str):
    """延迟导入重量级服务，减少非相关模块的启动成本。"""
    if name == "TextModelService":
        from .text_model_service import TextModelService

        return TextModelService
    if name == "ImageModelService":
        from .image_model_service import ImageModelService

        return ImageModelService
    if name == "VoiceModelService":
        from .voice_model_service import VoiceModelService

        return VoiceModelService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
