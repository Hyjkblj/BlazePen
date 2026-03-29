"""Training identity preset registry and request hydration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrainingIdentityPreset:
    """Canonical preset definition for training portrait generation."""

    code: str
    title: str
    description: str
    identity_label: str
    default_name: str
    default_gender: str
    appearance_keywords: tuple[str, ...]
    personality_keywords: tuple[str, ...]
    style: str
    scene_tone: str = "1937-1945 wartime documentary realism"
    palette: str = "desaturated grayscale with dark red accents"
    lighting: str = "cinematic side backlight and volumetric fog"


TRAINING_IDENTITY_PRESET_MAP: dict[str, TrainingIdentityPreset] = {
    "correspondent-female": TrainingIdentityPreset(
        code="correspondent-female",
        title="女记者形象",
        description="冷静、坚定，适合叙事主视觉。",
        identity_label="战地记者",
        default_name="前线女记者",
        default_gender="female",
        appearance_keywords=("lean", "short dark hair", "war correspondent coat"),
        personality_keywords=("calm", "resolute", "responsible"),
        style="wartime documentary realism with dark red accents",
    ),
    "correspondent-male": TrainingIdentityPreset(
        code="correspondent-male",
        title="男记者形象",
        description="沉稳、克制，强调纪实视角。",
        identity_label="战地记者",
        default_name="前线男记者",
        default_gender="male",
        appearance_keywords=("short hair", "rugged", "war correspondent coat"),
        personality_keywords=("calm", "disciplined", "reliable"),
        style="wartime documentary realism with dark red accents",
    ),
    "frontline-photographer": TrainingIdentityPreset(
        code="frontline-photographer",
        title="摄影记者形象",
        description="突出镜头语言与现场张力。",
        identity_label="摄影记者",
        default_name="前线摄影记者",
        default_gender="male",
        appearance_keywords=("vintage camera", "field gear", "focused look"),
        personality_keywords=("decisive", "alert", "fearless"),
        style="battlefield reportage tone with smoke and ruins",
    ),
    "radio-operator": TrainingIdentityPreset(
        code="radio-operator",
        title="通讯员形象",
        description="强调联络与信息传递职责。",
        identity_label="通讯联络员",
        default_name="战地通讯员",
        default_gender="female",
        appearance_keywords=("radio headset", "field uniform", "compact posture"),
        personality_keywords=("careful", "steady", "team-oriented"),
        style="wartime communication outpost with tense atmosphere",
    ),
}


class UnknownTrainingIdentityCodeError(ValueError):
    """Raised when a provided identity_code does not exist in registry."""

    def __init__(self, identity_code: str, supported_codes: list[str]):
        self.identity_code = identity_code
        self.supported_codes = tuple(supported_codes)
        super().__init__(
            f"unsupported identity_code: {identity_code}. "
            f"supported identity_code values: {', '.join(supported_codes)}"
        )


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _normalize_gender(value: Any, fallback: str) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return fallback

    lowered = normalized.lower()
    if lowered in {"male", "m", "man", "男"}:
        return "male"
    if lowered in {"female", "f", "woman", "女"}:
        return "female"
    return fallback


def list_training_identity_presets() -> list[dict[str, Any]]:
    """Return UI-safe metadata used to render available identity presets."""

    items: list[dict[str, Any]] = []
    for preset in TRAINING_IDENTITY_PRESET_MAP.values():
        items.append(
            {
                "code": preset.code,
                "title": preset.title,
                "description": preset.description,
                "identity": preset.identity_label,
                "default_name": preset.default_name,
                "default_gender": preset.default_gender,
            }
        )
    return items


def resolve_character_request_identity_preset(request_data: dict[str, Any]) -> dict[str, Any]:
    """Hydrate prompt-relevant fields from identity_code on backend side.

    When identity_code is provided, backend-owned preset fields become the source of truth
    for prompt construction (`appearance`, `personality`, `background`). User-entered
    profile fields (`name`, `identity`, `gender`, `age`) are still respected.
    """

    identity_code = _normalize_optional_string(request_data.get("identity_code"))
    if identity_code is None:
        return request_data

    preset = TRAINING_IDENTITY_PRESET_MAP.get(identity_code)
    if preset is None:
        raise UnknownTrainingIdentityCodeError(
            identity_code=identity_code,
            supported_codes=sorted(TRAINING_IDENTITY_PRESET_MAP.keys()),
        )

    resolved_name = _normalize_optional_string(request_data.get("name")) or preset.default_name
    resolved_identity = _normalize_optional_string(request_data.get("identity")) or preset.identity_label
    resolved_gender = _normalize_gender(request_data.get("gender"), preset.default_gender)

    resolved_data = dict(request_data)
    resolved_data.update(
        {
            "identity_code": preset.code,
            "name": resolved_name,
            "identity": resolved_identity,
            "gender": resolved_gender,
            "appearance": {
                "keywords": list(preset.appearance_keywords),
                "scene_tone": preset.scene_tone,
            },
            "personality": {
                "keywords": list(preset.personality_keywords),
                "identity": resolved_identity,
            },
            "background": {
                "style": preset.style,
                "palette": preset.palette,
                "lighting": preset.lighting,
            },
        }
    )
    return resolved_data
