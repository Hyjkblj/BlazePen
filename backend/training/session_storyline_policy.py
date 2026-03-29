"""Session storyline expansion policy for guided training."""

from __future__ import annotations

from hashlib import sha256
from random import Random
from typing import Any, Dict, Iterable, List, Sequence
from uuid import uuid4

from training.scenario_repository import ScenarioRepository


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(values: Iterable[Any] | None) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = _normalize_text(value)
        if not text or text in normalized:
            continue
        normalized.append(text)
    return normalized


def _merge_unique_lists(*groups: Iterable[Any]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        for item in _normalize_text_list(group):
            if item not in merged:
                merged.append(item)
    return merged


class SessionStorylinePolicy:
    """Builds a continuous major+micro storyline used by one training session."""

    _FIXED_CAST: Sequence[Dict[str, str]] = (
        {"name": "陈编辑", "role": "总编把关"},
        {"name": "赵川", "role": "前线通讯员"},
        {"name": "林岚", "role": "摄影记者"},
        {"name": "老何", "role": "印刷与发布"},
        {"name": "周联络", "role": "群众反馈联络"},
    )

    _MICRO_SCENE_BLUEPRINTS: Sequence[Dict[str, Any]] = (
        {
            "title": "快讯核验窗口",
            "focus": "多源冲突下的事实核验与分层发布",
            "risk_tags": ("verification_chain", "rumor"),
            "skill_bias": ("K1", "K2", "K6"),
            "mission_template": (
                "{cast_1}与{cast_2}同步带回冲突口径。"
                "你需要在不打断主线推进的前提下，给出一版可发布与待核验并行的处理方案。"
            ),
            "options": (
                (
                    "先整合全部线索做统一快讯",
                    "速度快，但可能把未核验内容一起放大。",
                ),
                (
                    "分层发布：已核实内容先发，争议内容标注待核验",
                    "连续性更好，也能控制失真风险。",
                ),
                (
                    "暂缓发布，直到全部来源一致",
                    "风险最低，但可能错过关键传播窗口。",
                ),
            ),
        },
        {
            "title": "编辑会审节点",
            "focus": "编辑协同与发布边界设定",
            "risk_tags": ("headline_pressure", "editor_trust"),
            "skill_bias": ("K4", "K6", "K8"),
            "mission_template": (
                "{cast_1}要求你在10分钟内给出可执行稿纲。"
                "你需要明确标题边界、证据边界与后续更新机制。"
            ),
            "options": (
                (
                    "强调冲突与情绪，先把传播做大",
                    "短期声量上升，但会削弱信任与可控性。",
                ),
                (
                    "按事实层级组织稿纲并附更新触发条件",
                    "兼顾发布效率与稳定协同。",
                ),
                (
                    "把关键判断留给后续班次处理",
                    "降低当下压力，但可能导致链路断点。",
                ),
            ),
        },
        {
            "title": "现场回访节点",
            "focus": "来源保护与可追溯证据表达",
            "risk_tags": ("source_safety", "privacy_leak"),
            "skill_bias": ("K2", "K5", "K6"),
            "mission_template": (
                "{cast_2}反馈有目击者愿意补充证词，但对身份暴露极其敏感。"
                "你需要完成一版既可核查又不暴露线人的描述。"
            ),
            "options": (
                (
                    "公开证词细节与可识别背景",
                    "证据感强，但来源风险极高。",
                ),
                (
                    "匿名化关键信息并保留核查链条",
                    "更符合长期来源保护与持续采访。",
                ),
                (
                    "删除全部细节，仅保留模糊结论",
                    "安全性高，但信息价值明显下降。",
                ),
            ),
        },
        {
            "title": "公众沟通节点",
            "focus": "风险提示与行动指引并行",
            "risk_tags": ("public_panic", "action_guidance"),
            "skill_bias": ("K4", "K7", "K8"),
            "mission_template": (
                "群众反馈出现明显波动，{cast_1}希望你补一段“怎么做”的指引。"
                "你需要让信息可执行、可理解且不过度煽动。"
            ),
            "options": (
                (
                    "放大最坏后果，强迫立刻行动",
                    "执行率可能上升，但恐慌风险同步上升。",
                ),
                (
                    "说明风险级别并给出分步骤行动清单",
                    "有助于稳态传播与组织协同。",
                ),
                (
                    "淡化风险，避免影响现场秩序",
                    "短期安静，但后续信任可能受损。",
                ),
            ),
        },
        {
            "title": "发布复盘节点",
            "focus": "纠偏闭环与后续版本管理",
            "risk_tags": ("correction_loop", "credibility_repair"),
            "skill_bias": ("K5", "K6", "K8"),
            "mission_template": (
                "上一版本出现表达歧义，{cast_2}要求你在不打断主线的情况下完成纠偏。"
                "请给出撤回范围、替代表达与下一次更新时间。"
            ),
            "options": (
                (
                    "仅调整标题，不解释调整原因",
                    "改动快，但修复力度不足。",
                ),
                (
                    "明确纠偏原因并同步替代表达与更新时间",
                    "最有利于恢复信任与流程稳定。",
                ),
                (
                    "将问题归因于单一消息源并继续发布",
                    "短期省事，但风险会累积。",
                ),
            ),
        },
    )

    def __init__(
        self,
        *,
        scenario_repository: ScenarioRepository | None = None,
        micro_scene_min: int = 2,
        micro_scene_max: int = 3,
    ):
        self.scenario_repository = scenario_repository or ScenarioRepository()
        self.micro_scene_min = max(int(micro_scene_min), 1)
        self.micro_scene_max = max(int(micro_scene_max), self.micro_scene_min)

    def build_session_sequence(
        self,
        *,
        training_mode: str,
        base_sequence: Sequence[Dict[str, Any]] | None,
        player_profile: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:
        """Expand default major scenes into a continuous major+micro route."""
        normalized_base = self._normalize_base_sequence(base_sequence)
        if not normalized_base:
            return []

        if not self._should_expand_storyline(training_mode=training_mode, player_profile=player_profile):
            return normalized_base

        storyline_seed = self._resolve_storyline_seed(player_profile)
        storyline_id = self._build_storyline_id(storyline_seed)
        rng = Random(self._seed_to_int(storyline_seed))
        player_identity = _normalize_text((player_profile or {}).get("identity")) or "记者"

        expanded_sequence: List[Dict[str, Any]] = []
        previous_scene_title = "序章"
        previous_scene_id = ""

        for major_index, base_item in enumerate(normalized_base, start=1):
            major_payload = self._build_major_scene_payload(
                base_item=base_item,
                major_index=major_index,
                total_majors=len(normalized_base),
                previous_scene_title=previous_scene_title,
                storyline_id=storyline_id,
            )
            expanded_sequence.append(major_payload)
            previous_scene_title = str(major_payload.get("title") or previous_scene_title)
            previous_scene_id = str(major_payload.get("id") or previous_scene_id)

            micro_count = rng.randint(self.micro_scene_min, self.micro_scene_max)
            micro_blueprints = self._pick_micro_blueprints(rng=rng, count=micro_count)
            for micro_index, blueprint in enumerate(micro_blueprints, start=1):
                micro_payload = self._build_micro_scene_payload(
                    major_payload=major_payload,
                    major_index=major_index,
                    micro_index=micro_index,
                    previous_scene_title=previous_scene_title,
                    previous_scene_id=previous_scene_id,
                    storyline_id=storyline_id,
                    player_identity=player_identity,
                    blueprint=blueprint,
                )
                expanded_sequence.append(micro_payload)
                previous_scene_title = str(micro_payload.get("title") or previous_scene_title)
                previous_scene_id = str(micro_payload.get("id") or previous_scene_id)

        self._inject_storyline_links(expanded_sequence, storyline_id=storyline_id)
        return expanded_sequence or normalized_base

    def _should_expand_storyline(
        self,
        *,
        training_mode: str,
        player_profile: Dict[str, Any] | None,
    ) -> bool:
        if not isinstance(player_profile, dict):
            return False
        if bool(player_profile.get("disable_storyline_expansion")):
            return False
        if bool(player_profile.get("force_storyline_expansion")):
            return True

        normalized_mode = _normalize_text(training_mode).lower().replace("_", "-")
        if normalized_mode != "guided":
            return False

        return bool(_normalize_text(player_profile.get("identity")))

    def _normalize_base_sequence(self, base_sequence: Sequence[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in base_sequence or []:
            if not isinstance(item, dict):
                continue
            scenario_id = _normalize_text(item.get("id"))
            if not scenario_id:
                continue
            payload = dict(item)
            payload["id"] = scenario_id
            payload["title"] = _normalize_text(item.get("title")) or scenario_id
            normalized.append(payload)
        return normalized

    def _build_major_scene_payload(
        self,
        *,
        base_item: Dict[str, Any],
        major_index: int,
        total_majors: int,
        previous_scene_title: str,
        storyline_id: str,
    ) -> Dict[str, Any]:
        major_id = _normalize_text(base_item.get("id"))
        repository_payload = self.scenario_repository.get_scenario(major_id) or {}

        payload = dict(repository_payload)
        for key, value in dict(base_item).items():
            if value is not None:
                payload[key] = value

        title = _normalize_text(payload.get("title")) or major_id
        phase_tags = _normalize_text_list(payload.get("phase_tags")) or self._fallback_phase_tags(major_index)
        target_skills = _normalize_text_list(payload.get("target_skills"))
        risk_tags = _normalize_text_list(payload.get("risk_tags"))
        options = self._normalize_options(payload.get("options"))

        if not options:
            options = self._build_default_major_options()

        active_cast = self._pick_active_cast(major_index=major_index, micro_index=0)
        cast_display = "、".join([f"{item['name']}({item['role']})" for item in active_cast])

        raw_brief = _normalize_text(payload.get("brief"))
        bridged_brief = (
            f"主线第{major_index}/{total_majors}幕，承接“{previous_scene_title}”。"
            f"固定角色协同：{cast_display}。"
        )
        if raw_brief:
            bridged_brief = f"{bridged_brief}{raw_brief}"

        raw_mission = _normalize_text(payload.get("mission"))
        mission = raw_mission or "在高压时限内完成可发布方案，并保证信息连续、可核验。"
        mission = f"{mission}（完成后进入本幕小场景，且每个小场景都参与测评）"

        payload.update(
            {
                "id": major_id,
                "title": title,
                "brief": bridged_brief,
                "mission": mission,
                "decision_focus": _normalize_text(payload.get("decision_focus"))
                or "主线推进中的事实边界与发布边界",
                "phase_tags": phase_tags,
                "branch_tags": _merge_unique_lists(payload.get("branch_tags"), ["mainline", "major_scene"]),
                "target_skills": target_skills,
                "risk_tags": risk_tags,
                "options": options,
                "completion_hint": _normalize_text(payload.get("completion_hint"))
                or "给出可执行方案，并说明如何与下一节点衔接。",
                # Keep the major+micro route continuous and avoid runtime branch jumps.
                "next_rules": [],
                "scene_level": "major",
                "major_scene_id": major_id,
                "major_scene_order": major_index,
                "storyline_id": storyline_id,
                "active_cast": active_cast,
                "is_assessment_round": True,
            }
        )
        return payload

    def _build_micro_scene_payload(
        self,
        *,
        major_payload: Dict[str, Any],
        major_index: int,
        micro_index: int,
        previous_scene_title: str,
        previous_scene_id: str,
        storyline_id: str,
        player_identity: str,
        blueprint: Dict[str, Any],
    ) -> Dict[str, Any]:
        major_id = _normalize_text(major_payload.get("id"))
        major_title = _normalize_text(major_payload.get("title")) or major_id
        active_cast = self._pick_active_cast(major_index=major_index, micro_index=micro_index)

        cast_1 = active_cast[0]["name"]
        cast_2 = active_cast[1]["name"]
        title = f"{major_title}·小场景{micro_index}·{_normalize_text(blueprint.get('title'))}"
        location = _normalize_text(major_payload.get("location")) or "前线联合工作点"
        mission_template = _normalize_text(blueprint.get("mission_template"))
        mission = mission_template.format(
            cast_1=cast_1,
            cast_2=cast_2,
            player_identity=player_identity,
            major_title=major_title,
        )
        brief = (
            f"承接上一节点“{previous_scene_title}”。"
            f"{cast_1}与{cast_2}在{location}提出新的变量，本小场景结果将直接影响后续主线。"
        )

        major_skills = _normalize_text_list(major_payload.get("target_skills"))
        target_skills = _merge_unique_lists(blueprint.get("skill_bias"), major_skills)[:4]
        major_risk_tags = _normalize_text_list(major_payload.get("risk_tags"))
        risk_tags = _merge_unique_lists(major_risk_tags, blueprint.get("risk_tags"), ["micro_scene"])

        options = self._build_micro_options(blueprint)
        if not options:
            options = self._build_default_major_options()

        micro_scene_id = f"{major_id}_micro_{major_index}_{micro_index}_{storyline_id[-8:]}"
        payload = {
            "id": micro_scene_id,
            "title": title,
            "era_date": _normalize_text(major_payload.get("era_date")),
            "location": location,
            "brief": brief,
            "mission": mission,
            "decision_focus": _normalize_text(blueprint.get("focus")) or "连续推进中的局部决策与交接质量",
            "phase_tags": _normalize_text_list(major_payload.get("phase_tags")),
            "branch_tags": _merge_unique_lists(major_payload.get("branch_tags"), ["mainline", "micro_scene"]),
            "target_skills": target_skills,
            "risk_tags": risk_tags,
            "options": options,
            "completion_hint": "说明你的选择如何与上一节点保持连续，并为下一节点留出可执行交接。",
            "next_rules": [],
            "scene_level": "micro",
            "major_scene_id": major_id,
            "major_scene_order": major_index,
            "micro_scene_order": micro_index,
            "storyline_anchor_scene_id": previous_scene_id,
            "storyline_id": storyline_id,
            "active_cast": active_cast,
            "is_assessment_round": True,
        }
        return payload

    def _build_micro_options(self, blueprint: Dict[str, Any]) -> List[Dict[str, str]]:
        raw_options = list(blueprint.get("options") or [])
        if not raw_options:
            return []

        normalized: List[Dict[str, str]] = []
        for index, option_item in enumerate(raw_options[:3], start=0):
            if not isinstance(option_item, (list, tuple)) or len(option_item) < 2:
                continue
            label = _normalize_text(option_item[0])
            impact_hint = _normalize_text(option_item[1])
            if not label:
                continue
            normalized.append(
                {
                    "id": ["A", "B", "C"][index],
                    "label": label,
                    "impact_hint": impact_hint,
                }
            )
        return normalized

    def _build_default_major_options(self) -> List[Dict[str, str]]:
        return [
            {
                "id": "A",
                "label": "快速发布当前线索，后续再补核验",
                "impact_hint": "时效快，但失真风险更高。",
            },
            {
                "id": "B",
                "label": "先补足关键核验，再给出可发布版本",
                "impact_hint": "更稳健，兼顾准确性与连续推进。",
            },
            {
                "id": "C",
                "label": "发布已确认事实并标注待核查部分",
                "impact_hint": "有助于建立更新闭环与信任。",
            },
        ]

    def _normalize_options(self, options: Any) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for option in options or []:
            if not isinstance(option, dict):
                continue
            option_id = _normalize_text(option.get("id"))
            if not option_id:
                continue
            normalized.append(
                {
                    "id": option_id,
                    "label": _normalize_text(option.get("label")) or option_id,
                    "impact_hint": _normalize_text(option.get("impact_hint")),
                }
            )
        return normalized

    def _pick_active_cast(self, *, major_index: int, micro_index: int) -> List[Dict[str, str]]:
        cast_size = len(self._FIXED_CAST)
        first_index = (major_index + micro_index) % cast_size
        second_index = (major_index + micro_index + 2) % cast_size
        first = dict(self._FIXED_CAST[first_index])
        second = dict(self._FIXED_CAST[second_index])
        if first["name"] == second["name"]:
            second = dict(self._FIXED_CAST[(second_index + 1) % cast_size])
        return [first, second]

    def _pick_micro_blueprints(self, *, rng: Random, count: int) -> List[Dict[str, Any]]:
        blueprints = list(self._MICRO_SCENE_BLUEPRINTS)
        selected: List[Dict[str, Any]] = []

        for _ in range(max(int(count), 0)):
            if blueprints:
                index = rng.randrange(len(blueprints))
                selected.append(dict(blueprints.pop(index)))
                continue
            # Fallback to replacement sampling when requested count > blueprint size.
            selected.append(dict(self._MICRO_SCENE_BLUEPRINTS[rng.randrange(len(self._MICRO_SCENE_BLUEPRINTS))]))
        return selected

    def _inject_storyline_links(
        self,
        sequence: List[Dict[str, Any]],
        *,
        storyline_id: str,
    ) -> None:
        total = len(sequence)
        for index, payload in enumerate(sequence):
            previous_scene_id = str(sequence[index - 1].get("id") or "") if index > 0 else None
            next_scene_id = str(sequence[index + 1].get("id") or "") if index + 1 < total else None
            payload["storyline_id"] = storyline_id
            payload["storyline_order"] = index + 1
            payload["storyline_total"] = total
            payload["storyline_prev_scene_id"] = previous_scene_id
            payload["storyline_next_scene_id"] = next_scene_id

    def _resolve_storyline_seed(self, player_profile: Dict[str, Any] | None) -> str:
        if isinstance(player_profile, dict):
            explicit_seed = _normalize_text(
                player_profile.get("script_seed") or player_profile.get("storyline_seed")
            )
            if explicit_seed:
                return explicit_seed
            profile_signature = "|".join(
                [
                    _normalize_text(player_profile.get("name")),
                    _normalize_text(player_profile.get("identity")),
                    _normalize_text(player_profile.get("gender")),
                ]
            ).strip("|")
            if profile_signature:
                return f"{profile_signature}|{uuid4().hex}"
        return uuid4().hex

    def _build_storyline_id(self, seed: str) -> str:
        digest = sha256(str(seed).encode("utf-8")).hexdigest()
        return f"storyline_{digest[:12]}"

    def _seed_to_int(self, value: str) -> int:
        digest = sha256(str(value).encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _fallback_phase_tags(self, major_index: int) -> List[str]:
        if major_index <= 2:
            return ["opening"]
        if major_index <= 4:
            return ["middle"]
        if major_index == 5:
            return ["climax"]
        return ["closing"]
