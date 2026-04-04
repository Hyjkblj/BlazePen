"""LLM-driven training story script agent.

Generates a continuous storyline:
- 6 major scenes (based on frozen scenario bank)
- 2 micro scenes between each adjacent major scene (total 10 micro scenes)
- Each scene contains monologue and dialogues with fixed cast.

Storage rule:
- Each training session_id owns exactly one script row.
- Scripts are generated per-session (no cross-session cloning). If product needs reuse later,
  introduce a dedicated, versioned template library domain instead of sampling real sessions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from random import Random
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.text_model_service import TextModelService
from utils.logger import get_logger


logger = get_logger(__name__)


class StoryScriptLine(BaseModel):
    speaker: str = Field(..., description="角色名，如：旁白/玩家/陈编辑/赵川/林岚/老何/周联络")
    content: str = Field(..., description="台词内容")

class StoryScriptOption(BaseModel):
    option_id: str = Field(..., description="选项 id：opt-1/opt-2/opt-3")
    label: str = Field(..., description="玩家可选动作（短句）")
    impact_hint: str = Field(default="", description="影响提示（短句）")


class StoryScriptScene(BaseModel):
    scene_id: str = Field(..., description="唯一 id，例如 major-1 / micro-1-1")
    scene_type: str = Field(..., description="major or micro")
    title: str = Field(..., description="场景标题")
    time_hint: str = Field(default="", description="时间提示，可空")
    location_hint: str = Field(default="", description="地点提示，可空")
    monologue: str = Field(default="", description="玩家内心独白/旁白独白")
    dialogue: List[StoryScriptLine] = Field(default_factory=list, description="对话列表")
    bridge_summary: str = Field(default="", description="承上启下的一句话，用于连续性")
    options: List[StoryScriptOption] = Field(default_factory=list, description="玩家选项（必须 3 个）")


class TrainingStoryScriptPayload(BaseModel):
    version: str = Field(default="training_story_script_v1")
    cast: List[Dict[str, str]] = Field(default_factory=list)
    major_scenes: List[Dict[str, Any]] = Field(default_factory=list, description="用于生成时的输入摘要，可回溯")
    scenes: List[StoryScriptScene] = Field(default_factory=list)


def build_training_scenario_payload_sequence_from_story_script(
    payload: Dict[str, Any],
    *,
    major_scene_sources: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Map LLM story-script payload into training scenario payload sequence used by session snapshots."""

    from training.exceptions import TrainingStoryScriptInvalidError

    validated = TrainingStoryScriptPayload.model_validate(payload)
    major_sources = [dict(item) for item in (major_scene_sources or []) if isinstance(item, dict)]

    def resolve_major_source_for_scene_id(scene_id: str) -> Dict[str, Any]:
        # Use scene_id index mapping (stable) instead of title matching.
        text = str(scene_id or "").strip().lower()
        if text.startswith("major-"):
            try:
                index = int(text.split("-", 1)[1])
            except Exception:
                index = 0
            return major_sources[index - 1] if 1 <= index <= len(major_sources) else {}
        if text.startswith("micro-"):
            # micro-<majorIndex>-<k> maps to the preceding major index
            parts = text.split("-")
            try:
                major_index = int(parts[1])
            except Exception:
                major_index = 0
            return major_sources[major_index - 1] if 1 <= major_index <= len(major_sources) else {}
        return {}

    sequence: List[Dict[str, Any]] = []
    for index, scene in enumerate(validated.scenes, start=1):
        scene_title = str(scene.title or "").strip() or scene.scene_id
        major_src = resolve_major_source_for_scene_id(scene.scene_id)
        scenario_id = f"llm-{scene.scene_id}"
        scenario_payload: Dict[str, Any] = {
            "id": scenario_id,
            "title": scene_title,
            "era_date": str(major_src.get("era_date") or major_src.get("eraDate") or ""),
            "location": str(major_src.get("location") or ""),
            "brief": str(getattr(scene, "monologue", "") or ""),
            "mission": str(major_src.get("mission") or ""),
            "decision_focus": str(major_src.get("decision_focus") or major_src.get("decisionFocus") or ""),
            "phase_tags": ["llm_script", str(scene.scene_type or "").strip() or "scene"],
            "branch_tags": [],
            "target_skills": list(major_src.get("target_skills") or []),
            "risk_tags": list(major_src.get("risk_tags") or []),
            "completion_hint": str(scene.bridge_summary or ""),
            "next_rules": [{"go_to": "", "default": True, "transition_type": "linear"}],
        }

        options_payload: List[Dict[str, Any]] = []
        raw_options = list(scene.options or [])
        if len(raw_options) != 3:
            raise TrainingStoryScriptInvalidError(
                "story script scene options must be exactly 3",
                details={"scene_id": scene.scene_id, "options_count": len(raw_options)},
            )

        for opt_idx, option in enumerate(raw_options, start=1):
            if not str(option.label or "").strip():
                raise TrainingStoryScriptInvalidError(
                    "story script option label is required",
                    details={"scene_id": scene.scene_id, "option_index": opt_idx},
                )
            option_id = f"{scenario_id}-opt-{opt_idx}"
            options_payload.append(
                {
                    "id": option_id,
                    "label": str(option.label or "").strip(),
                    "impact_hint": str(option.impact_hint or "").strip(),
                    "label_variants": [],
                    "impact_hint_variants": [],
                }
            )
        scenario_payload["options"] = options_payload
        scenario_payload["scene_dialogue"] = [
            {"speaker": str(line.speaker), "content": str(line.content)}
            for line in (scene.dialogue or [])
        ]
        scenario_payload["scene_meta"] = {
            "script_scene_id": scene.scene_id,
            "script_scene_type": scene.scene_type,
            "sequence_index": index,
            "major_source_id": str(major_src.get("id") or "").strip() or None,
        }
        sequence.append(scenario_payload)

    return sequence


@dataclass(frozen=True)
class StoryScriptAgentConfig:
    major_scene_count: int = 6
    micro_scenes_per_gap: int = 2
    temperature: float = 0.65
    max_tokens: int = 2600


class StoryScriptAgent:
    def __init__(
        self,
        *,
        training_store: Any,
        text_model_service: Optional[TextModelService] = None,
        config: StoryScriptAgentConfig | None = None,
    ):
        self.training_store = training_store
        self.text_model_service = text_model_service or TextModelService()
        self.config = config or StoryScriptAgentConfig()

    def ensure_script_for_session(
        self,
        *,
        session_id: str,
        major_scene_sources: List[Dict[str, Any]],
        player_profile: Dict[str, Any] | None = None,
        allow_llm: bool = True,
    ) -> Dict[str, Any]:
        """Return payload for this session, creating/cloning if needed."""

        existing = self.training_store.get_story_script_by_session_id(session_id)
        if existing is not None:
            payload = getattr(existing, "payload", None) or {}
            if isinstance(payload, dict) and payload:
                return dict(payload)

        # NOTE: Do not clone scripts from other real sessions (privacy/consistency risk).
        # A dedicated template library can be introduced later if product requires reuse.

        return self._generate_and_store(
            session_id=session_id,
            major_scene_sources=major_scene_sources,
            player_profile=player_profile,
            allow_llm=allow_llm,
        )

    def _generate_and_store(
        self,
        *,
        session_id: str,
        major_scene_sources: List[Dict[str, Any]],
        player_profile: Dict[str, Any] | None,
        allow_llm: bool,
    ) -> Dict[str, Any]:
        payload = (
            self._call_llm_generate_payload(
                session_id=session_id,
                major_scene_sources=major_scene_sources,
                player_profile=player_profile,
            )
            if allow_llm
            else self._call_local_fallback_payload(
                session_id=session_id,
                major_scene_sources=major_scene_sources,
                player_profile=player_profile,
            )
        )
        provider = self.text_model_service.get_provider()
        model = self.text_model_service.get_model()
        fallback_used = bool(payload.get("fallback_used", False))
        created = self.training_store.create_story_script(
            session_id=session_id,
            payload=payload,
            provider=provider,
            model=model,
            major_scene_count=self.config.major_scene_count,
            micro_scenes_per_gap=self.config.micro_scenes_per_gap,
            source_script_id=None,
            status="ready",
            error_code=str(payload.get("error_code") or "").strip() or None,
            error_message=str(payload.get("error_message") or "").strip() or None,
            fallback_used=fallback_used,
        )
        # When the story script row already exists (pending/empty payload), create_story_script will
        # return the existing row due to session_id uniqueness. Ensure we still persist the payload.
        if created is not None and not dict(getattr(created, "payload", None) or {}):
            self.training_store.update_story_script_by_session_id(
                session_id,
                {
                    "provider": provider,
                    "model": model,
                    "major_scene_count": self.config.major_scene_count,
                    "micro_scenes_per_gap": self.config.micro_scenes_per_gap,
                    "status": "ready",
                    "error_code": str(payload.get("error_code") or "").strip() or None,
                    "error_message": str(payload.get("error_message") or "").strip() or None,
                    "fallback_used": fallback_used,
                    "payload": payload,
                },
            )
        return dict(getattr(created, "payload", None) or payload)

    def _call_local_fallback_payload(
        self,
        *,
        session_id: str,
        major_scene_sources: List[Dict[str, Any]],
        player_profile: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        cast = [
            {"name": "陈编辑", "role": "总编把关"},
            {"name": "赵川", "role": "前线通讯员"},
            {"name": "林岚", "role": "摄影记者"},
            {"name": "老何", "role": "印刷与发布"},
            {"name": "周联络", "role": "群众反馈联络"},
        ]
        player_name = str((player_profile or {}).get("name") or "玩家").strip() or "玩家"
        major_summaries = []
        for item in major_scene_sources or []:
            if not isinstance(item, dict):
                continue
            major_summaries.append(
                {
                    "id": str(item.get("id") or "").strip(),
                    "title": str(item.get("title") or "").strip(),
                    "era_date": str(item.get("era_date") or item.get("eraDate") or "").strip(),
                    "location": str(item.get("location") or "").strip(),
                    "brief": str(item.get("brief") or "").strip(),
                    "mission": str(item.get("mission") or "").strip(),
                    "decision_focus": str(item.get("decision_focus") or item.get("decisionFocus") or "").strip(),
                }
            )
        required_major = self.config.major_scene_count
        major_summaries = (major_summaries[:required_major] if major_summaries else []) or [
            {"id": f"major-{idx+1}", "title": f"主场景 {idx+1}", "brief": "", "mission": "", "decision_focus": ""}
            for idx in range(required_major)
        ]
        payload = self._build_local_fallback_payload(cast=cast, major_summaries=major_summaries, player_name=player_name)
        payload["fallback_used"] = True
        payload["generation_status"] = "succeeded"
        payload["error_code"] = None
        return payload

    def _call_llm_generate_payload(
        self,
        *,
        session_id: str,
        major_scene_sources: List[Dict[str, Any]],
        player_profile: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        cast = [
            {"name": "陈编辑", "role": "总编把关"},
            {"name": "赵川", "role": "前线通讯员"},
            {"name": "林岚", "role": "摄影记者"},
            {"name": "老何", "role": "印刷与发布"},
            {"name": "周联络", "role": "群众反馈联络"},
        ]
        player_name = str((player_profile or {}).get("name") or "玩家").strip() or "玩家"
        player_identity = str((player_profile or {}).get("identity") or "战地新闻工作者").strip() or "战地新闻工作者"

        major_summaries = []
        for item in major_scene_sources or []:
            if not isinstance(item, dict):
                continue
            major_summaries.append(
                {
                    "id": str(item.get("id") or "").strip(),
                    "title": str(item.get("title") or "").strip(),
                    "era_date": str(item.get("era_date") or item.get("eraDate") or "").strip(),
                    "location": str(item.get("location") or "").strip(),
                    "brief": str(item.get("brief") or "").strip(),
                    "mission": str(item.get("mission") or "").strip(),
                    "decision_focus": str(item.get("decision_focus") or item.get("decisionFocus") or "").strip(),
                }
            )
        major_summaries = [item for item in major_summaries if item.get("title")]

        required_major = self.config.major_scene_count
        major_summaries = (major_summaries[:required_major] if major_summaries else []) or [
            {"id": f"major-{idx+1}", "title": f"主场景 {idx+1}", "brief": "", "mission": "", "decision_focus": ""}
            for idx in range(required_major)
        ]

        total_micro = max(0, (required_major - 1) * self.config.micro_scenes_per_gap)
        total_scenes = required_major + total_micro

        system_message = (
            "你是一个严谨的剧本生成器。只输出严格 JSON，不要输出任何解释、Markdown、代码块标记。"
        )
        prompt = f"""
为一个训练系统生成连续剧本（要求剧情严格连续、人物关系一致、事件因果连贯）。

【玩家信息】
- 玩家名：{player_name}
- 玩家身份：{player_identity}

【固定角色（必须出现并保持人格一致）】
{json.dumps(cast, ensure_ascii=False)}

【输入：六个大场景摘要（按顺序）】
{json.dumps(major_summaries, ensure_ascii=False)}

【结构要求】
- 总场景数 = {total_scenes}
- 大场景数 = {required_major}（scene_type=major，scene_id=major-1..major-{required_major}）
- 每两个相邻大场景之间插入 {self.config.micro_scenes_per_gap} 个小场景（scene_type=micro，scene_id=micro-<majorIndex>-<k>）
- 每个 scene 必须包含：
  - title（标题）
  - monologue（独白，第一人称，体现玩家心理与伦理压力）
  - dialogue（至少 6 句，speaker/content；speaker 必须来自：旁白/玩家/{'/' .join([c['name'] for c in cast])}）
  - bridge_summary（一句话承接前后）
  - options（必须 3 个，option_id=opt-1/opt-2/opt-3，label/impact_hint 都要有内容）
- 对话要包含“事实核验、分层发布、来源保护、行动指引、编辑协同”等训练主题，但不要出现“这是训练/这是提示词/系统”等字样。

【输出 JSON Schema】
{{
  "version": "training_story_script_v1",
  "cast": [{{"name": "...", "role": "..."}}],
  "major_scenes": [...原样回填 major_summaries...],
  "scenes": [
    {{
      "scene_id": "major-1",
      "scene_type": "major",
      "title": "...",
      "time_hint": "",
      "location_hint": "",
      "monologue": "...",
      "dialogue": [{{"speaker": "...", "content": "..."}}],
      "bridge_summary": "...",
      "options": [{{"option_id":"opt-1","label":"...","impact_hint":"..."}}, {{"option_id":"opt-2","label":"...","impact_hint":"..."}}, {{"option_id":"opt-3","label":"...","impact_hint":"..."}}]
    }}
  ]
}}

【重要】
- 必须是可 JSON.parse 的合法 JSON
- 不要多余字段，不要尾随注释
- 保证 scenes 顺序与结构要求一致
""".strip()

        def _try_parse_payload(raw_text: str) -> Dict[str, Any]:
            parsed = json.loads(raw_text)
            return TrainingStoryScriptPayload.model_validate(parsed).model_dump()

        def _repair_to_strict_json(raw_text: str, *, error: Exception) -> str | None:
            system_fix = (
                "你是一个严格的 JSON 修复器。"
                "你的唯一输出必须是可被 JSON.parse 的合法 JSON，且必须符合给定的 schema。"
                "不要输出 Markdown、不要输出代码块、不要输出任何解释性文字。"
            )
            fix_prompt = f"""
你将收到一段“剧本生成输出”，它无法被解析为合法 JSON 或无法通过 schema 校验。
请在不改变语义的前提下，将其修复为严格合法的 JSON，并确保字段与结构完全符合 schema。

【schema（必须严格遵守，不要多字段）】
{{
  "version": "training_story_script_v1",
  "cast": [{{"name": "...", "role": "..."}}],
  "major_scenes": [...原样回填 major_summaries...],
  "scenes": [
    {{
      "scene_id": "major-1",
      "scene_type": "major|micro",
      "title": "...",
      "time_hint": "",
      "location_hint": "",
      "monologue": "...",
      "dialogue": [{{"speaker": "...", "content": "..."}}],
      "bridge_summary": "...",
      "options": [
        {{"option_id":"opt-1","label":"...","impact_hint":"..."}},
        {{"option_id":"opt-2","label":"...","impact_hint":"..."}},
        {{"option_id":"opt-3","label":"...","impact_hint":"..."}}
      ]
    }}
  ]
}}

【固定角色（speaker 只能来自这些名字或 旁白/玩家）】
{json.dumps(cast, ensure_ascii=False)}

【大场景摘要（major_scenes 必须原样回填，按顺序）】
{json.dumps(major_summaries, ensure_ascii=False)}

【解析/校验失败原因（参考用）】
{str(error)}

【需要修复的原始输出】
{raw_text}
""".strip()
            return self.text_model_service.generate_text(
                prompt=fix_prompt,
                system_message=system_fix,
                max_tokens=self.config.max_tokens,
                temperature=0.0,
                use_retry=True,
            )

        last_error: Exception | None = None
        for attempt in range(1, 3):
            raw = self.text_model_service.generate_text(
                prompt=prompt,
                system_message=system_message,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature if attempt == 1 else 0.35,
                use_retry=True,
            )
            if not raw:
                last_error = RuntimeError("LLM returned empty story script")
                continue
            try:
                payload = _try_parse_payload(raw)
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "story script attempt failed: session_id=%s attempt=%s error=%s",
                    session_id,
                    attempt,
                    str(exc),
                )
                repaired = _repair_to_strict_json(raw, error=exc)
                if repaired:
                    try:
                        payload = _try_parse_payload(repaired)
                        logger.info(
                            "story script repaired into strict JSON: session_id=%s attempt=%s",
                            session_id,
                            attempt,
                        )
                        break
                    except Exception as repair_exc:
                        last_error = repair_exc
                        logger.warning(
                            "story script repair attempt failed: session_id=%s attempt=%s error=%s",
                            session_id,
                            attempt,
                            str(repair_exc),
                        )
                continue
        else:
            logger.warning(
                "LLM story script generation unavailable; using local fallback: session_id=%s error=%s",
                session_id,
                str(last_error),
            )
            payload = self._build_local_fallback_payload(
                cast=cast,
                major_summaries=major_summaries,
                player_name=player_name,
            )
            payload["fallback_used"] = True
            payload["error_code"] = "LLM_UNAVAILABLE"
            payload["error_message"] = str(last_error) if last_error else "LLM unavailable"

        # Attach generation timestamp for troubleshooting (inside payload only).
        payload.setdefault("generated_at", datetime.utcnow().isoformat())
        return payload

    def _build_local_fallback_payload(
        self,
        *,
        cast: List[Dict[str, str]],
        major_summaries: List[Dict[str, Any]],
        player_name: str,
    ) -> Dict[str, Any]:
        """Build a deterministic, continuous script when LLM is unavailable."""

        required_major = self.config.major_scene_count
        micro_per_gap = self.config.micro_scenes_per_gap
        scenes: List[Dict[str, Any]] = []

        def mk_dialogue(seed_title: str) -> List[Dict[str, str]]:
            # 6 lines, fixed cast, lightly tied to title for continuity.
            return [
                {"speaker": "旁白", "content": f"{seed_title}的消息像风一样传开，你感到时间被挤压。"},
                {"speaker": "玩家", "content": "先把可核实的最小事实集钉住，再谈扩写。"},
                {"speaker": "陈编辑", "content": "标题边界要守住，证据链写清楚，更新机制要可执行。"},
                {"speaker": "赵川", "content": "前线口径不一，我能再去补一条核验线索，但窗口很短。"},
                {"speaker": "林岚", "content": "画面能证明一部分，但最敏感的细节要匿名化处理。"},
                {"speaker": "周联络", "content": "群众反应在升温，需要风险提示和行动指引一起给到。"},
            ]

        def mk_options() -> List[Dict[str, str]]:
            return [
                {"option_id": "opt-1", "label": "先发布已核实事实并标注待核验项", "impact_hint": "降低失真，保留更新空间"},
                {"option_id": "opt-2", "label": "补强证据链后再发布，延迟但更稳", "impact_hint": "可信度更高，但可能错过窗口"},
                {"option_id": "opt-3", "label": "先内部汇总并设定更新触发条件再对外", "impact_hint": "协同更顺，但传播更克制"},
            ]

        for major_index in range(1, required_major + 1):
            major = major_summaries[major_index - 1] if major_index - 1 < len(major_summaries) else {}
            title = str(major.get("title") or f"主场景 {major_index}")
            era_date = str(major.get("era_date") or "").strip()
            location = str(major.get("location") or "").strip()
            scenes.append(
                {
                    "scene_id": f"major-{major_index}",
                    "scene_type": "major",
                    "title": title,
                    "time_hint": era_date,
                    "location_hint": location,
                    "monologue": f"我（{player_name}）知道每一句话都可能改变局势：既要快，也要真，还要护住人。",
                    "dialogue": mk_dialogue(title),
                    "bridge_summary": "你把已核实与待核验分层归档，准备进入下一步。",
                    "options": mk_options(),
                }
            )

            if major_index < required_major:
                for micro_k in range(1, micro_per_gap + 1):
                    micro_title = f"{title}后的快讯窗口 {micro_k}"
                    scenes.append(
                        {
                            "scene_id": f"micro-{major_index}-{micro_k}",
                            "scene_type": "micro",
                            "title": micro_title,
                            "time_hint": "",
                            "location_hint": location,
                            "monologue": "我在心里反复确认：哪些能说，哪些必须留在内部核验链条里。",
                            "dialogue": mk_dialogue(micro_title),
                            "bridge_summary": "信息流被重新校准，你带着更清晰的边界回到主线。",
                            "options": mk_options(),
                        }
                    )

        return TrainingStoryScriptPayload(
            cast=cast,
            major_scenes=major_summaries,
            scenes=[StoryScriptScene.model_validate(item) for item in scenes],
        ).model_dump()

