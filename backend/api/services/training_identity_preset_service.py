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
    appearance_keywords: tuple[str, ...]
    personality_keywords: tuple[str, ...]
    style: str
    scene_tone: str = "1937-1945 wartime documentary realism"
    palette: str = "desaturated grayscale with dark red accents"
    lighting: str = "cinematic side backlight and volumetric fog"


TRAINING_IDENTITY_PRESET_MAP: dict[str, TrainingIdentityPreset] = {
    "underground-reporter": TrainingIdentityPreset(
        code="underground-reporter",
        title="敌后笔锋・地下党报人",
        description="潜伏沦陷区，以笔为刃，用文章暗语传递情报，动摇日伪统治。",
        identity_label="地下党宣传线联络员",
        appearance_keywords=(
            "civilian clothes",
            "ink-stained fingers",
            "sharp observant eyes",
            "1940s Shanghai intellectual style",
        ),
        personality_keywords=("cunning", "composed", "persuasive", "vigilant"),
        style="occupied zone noir with dim lamplight and newspaper print texture",
        scene_tone="1937-1945 occupied China underground resistance",
        palette="sepia tones with muted red propaganda poster accents",
        lighting="low-key interior lamplight with deep shadows",
    ),
    "frontline-war-correspondent": TrainingIdentityPreset(
        code="frontline-war-correspondent",
        title="火线记录者・随军战地记者",
        description="跟随八路军转战敌后，记录烽火瞬间，兼任侦察与通讯职责。",
        identity_label="八路军政治部宣传科战斗员",
        appearance_keywords=(
            "military field uniform",
            "worn leather satchel",
            "rugged weathered face",
            "determined gaze",
        ),
        personality_keywords=("brave", "disciplined", "resilient", "loyal"),
        style="battlefield documentary realism with smoke dust and ruins",
        scene_tone="1937-1945 Eighth Route Army guerrilla warfare",
        palette="desaturated earth tones with gunpowder grey",
        lighting="harsh outdoor daylight with dramatic smoke backlight",
    ),
    "photo-intelligence": TrainingIdentityPreset(
        code="photo-intelligence",
        title="镜头暗战・摄影情报员",
        description="以相机为武器，深入日伪核心区域，在暗房中解密传递关键情报。",
        identity_label="地下党情报线摄影专员",
        appearance_keywords=(
            "vintage Leica camera",
            "dark overcoat",
            "calm analytical expression",
            "nimble posture",
        ),
        personality_keywords=("meticulous", "patient", "perceptive", "stealthy"),
        style="espionage thriller with darkroom chemical haze and film grain",
        scene_tone="1937-1945 wartime intelligence photography",
        palette="high-contrast black and white with amber darkroom glow",
        lighting="dramatic chiaroscuro with single-source darkroom red light",
    ),
    "newsboy-courier": TrainingIdentityPreset(
        code="newsboy-courier",
        title="街头信使・报童交通员",
        description="以卖报为掩护，穿梭沦陷区街头，传递情报、接送地下党员。",
        identity_label="地下党交通线联络员",
        appearance_keywords=(
            "worn street clothes",
            "newspaper bundle under arm",
            "quick alert eyes",
            "lean agile build",
        ),
        personality_keywords=("street-smart", "agile", "resourceful", "inconspicuous"),
        style="occupied city street realism with crowded market atmosphere",
        scene_tone="1937-1945 occupied city underground courier network",
        palette="dusty urban grey with faded newsprint yellow",
        lighting="harsh midday street light with alley shadow contrast",
    ),
    "concession-correspondent": TrainingIdentityPreset(
        code="concession-correspondent",
        title="租界喉舌・涉外记者",
        description="借租界身份周旋于各方势力，向国际社会揭露日军暴行，争取援助。",
        identity_label="中共地下党国际线联络员",
        appearance_keywords=(
            "1940s semi-western dress",
            "composed diplomatic bearing",
            "bilingual press badge",
            "elegant but cautious demeanor",
        ),
        personality_keywords=("diplomatic", "sharp-witted", "multilingual", "composed"),
        style="Shanghai concession intrigue with art deco interiors and tension",
        scene_tone="1937-1945 Shanghai International Settlement espionage",
        palette="warm art deco gold and deep navy with newsroom amber",
        lighting="soft interior chandelier light with window silhouette drama",
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


def list_training_identity_presets() -> list[dict[str, Any]]:
    """Return UI-safe metadata used to render available identity presets."""

    return [
        {
            "code": preset.code,
            "title": preset.title,
            "description": preset.description,
            "identity": preset.identity_label,
        }
        for preset in TRAINING_IDENTITY_PRESET_MAP.values()
    ]


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

    resolved_name = _normalize_optional_string(request_data.get("name")) or ""
    resolved_identity = _normalize_optional_string(request_data.get("identity")) or preset.identity_label

    resolved_data = dict(request_data)
    resolved_data.update(
        {
            "identity_code": preset.code,
            "name": resolved_name,
            "identity": resolved_identity,
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
