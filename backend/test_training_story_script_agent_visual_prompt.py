"""Unit tests for visual prompt semantics in StoryScriptAgent."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from training.story_script_agent import (
    StoryScriptAgent,
    _build_fallback_visual_prompt,
    resolve_narrative_for_scenario,
)


class _FakeTextModelService:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def generate_text(self, **kwargs):
        return self.response_text

    def get_provider(self):
        return "mock-provider"

    def get_model(self):
        return "mock-model"


def _build_fake_store():
    return SimpleNamespace(
        get_story_script_by_session_id=lambda session_id: None,
        update_story_script_by_session_id=lambda session_id, updates: None,
        create_story_script=lambda **kwargs: None,
    )


class StoryScriptAgentVisualPromptTests(unittest.TestCase):
    def test_fallback_visual_prompt_should_be_deterministic(self):
        scenario = {
            "id": "scenario-1",
            "title": "前线街头采访",
            "era_date": "1942-08-12",
            "location": "上海",
            "brief": "局势紧张，街区内存在不明交火声。",
        }

        first = _build_fallback_visual_prompt(scenario)
        second = _build_fallback_visual_prompt(dict(scenario))

        self.assertEqual(first, second)
        self.assertIn("前线街头采访", first)
        self.assertIn("上海", first)

    def test_fill_by_fallback_should_always_populate_visual_prompt(self):
        agent = StoryScriptAgent(
            training_store=_build_fake_store(),
            text_model_service=_FakeTextModelService("{}"),
        )
        scenarios = [
            {
                "id": "scenario-1",
                "title": "前线街头采访",
                "era_date": "1942-08-12",
                "location": "上海",
                "brief": "局势紧张，街区内存在不明交火声。",
            },
            {
                "id": "scenario-2",
                "title": "电台连线确认",
                "era_date": "1942-08-13",
                "location": "租界边缘",
                "brief": "多方口径不一致，需要二次核验。",
            },
        ]

        payload = agent._fill_by_fallback("session-visual-fallback", scenarios)
        narratives = payload.get("narratives", {})

        self.assertEqual(set(narratives.keys()), {"scenario-1", "scenario-2"})
        for sid in ["scenario-1", "scenario-2"]:
            visual_prompt = str(narratives[sid].get("visual_prompt") or "").strip()
            self.assertTrue(visual_prompt)
            self.assertIsInstance(narratives[sid].get("visual_elements"), list)

    def test_fill_by_llm_should_backfill_visual_prompt_when_missing(self):
        llm_payload = {
            "narratives": {
                "scenario-1": {
                    "monologue": "我要先确认事实，再决定发布节奏。",
                    "dialogue": [
                        {"speaker": "旁白", "content": "街口的风把传闻吹得更快。"},
                    ],
                    "bridge_summary": "你先固定了最小事实集。",
                    "options_narrative": {
                        "opt-1": {"option_id": "opt-1", "narrative_label": "先发已核实信息", "impact_hint": "稳妥推进"},
                        "opt-2": {"option_id": "opt-2", "narrative_label": "延迟发布补证据", "impact_hint": "可信度更高"},
                        "opt-3": {"option_id": "opt-3", "narrative_label": "内部复核后发布", "impact_hint": "协同更顺"},
                    },
                }
            }
        }
        agent = StoryScriptAgent(
            training_store=_build_fake_store(),
            text_model_service=_FakeTextModelService(json.dumps(llm_payload, ensure_ascii=False)),
        )
        scenarios = [
            {
                "id": "scenario-1",
                "title": "前线街头采访",
                "era_date": "1942-08-12",
                "location": "上海",
                "brief": "局势紧张，街区内存在不明交火声。",
                "mission": "在保护线人的前提下完成事实核验。",
            }
        ]

        payload = agent._fill_by_llm("session-visual-llm", scenarios)
        narrative = payload.get("narratives", {}).get("scenario-1", {})

        self.assertEqual(
            narrative.get("visual_prompt"),
            _build_fallback_visual_prompt(scenarios[0]),
        )
        self.assertEqual(narrative.get("visual_elements"), [])

    def test_resolve_narrative_for_scenario_should_default_visual_prompt_to_empty_string(self):
        payload = {
            "version": "training_story_script_v2",
            "narratives": {
                "scenario-1": {
                    "monologue": "独白",
                    "dialogue": [],
                    "bridge_summary": "",
                    "options_narrative": {},
                }
            },
        }

        narrative = resolve_narrative_for_scenario(payload, "scenario-1")
        self.assertEqual(narrative.get("visual_prompt"), "")
        self.assertEqual(narrative.get("visual_elements"), [])


if __name__ == "__main__":
    unittest.main()
