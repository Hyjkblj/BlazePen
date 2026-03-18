"""训练 CLI 剧本层单元测试。"""

from __future__ import annotations

import unittest

from training.cli_story_script import (
    build_round_feedback_story_block,
    build_scene_story_block,
    build_story_epilogue_block,
    build_story_prologue_block,
    build_transition_story_block,
)


class CliStoryScriptTestCase(unittest.TestCase):
    """验证剧本层的叙事结构稳定可用。"""

    def test_build_story_prologue_block_should_include_player_name_and_dialogues(self):
        """序章应带出玩家身份信息与编辑部对白。"""
        payload = build_story_prologue_block(
            player_profile={"name": "李敏", "identity": "战地记者"},
            training_mode="self-paced",
        )

        self.assertEqual(payload["title"], "序章：烽火笔锋")
        self.assertTrue(any("李敏" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any(dialogue["speaker"] == "陈编辑" for dialogue in payload["dialogues"]))
        self.assertTrue(any(dialogue["speaker"] == "印刷工老何" for dialogue in payload["dialogues"]))

    def test_build_scene_story_block_should_return_scene_specific_script_for_s1(self):
        """已配置场景应返回对应的历史化叙事内容。"""
        payload = build_scene_story_block(
            scenario={"id": "S1", "title": "卢沟桥事变快讯发布"},
            player_profile={"name": "李敏"},
            round_no=1,
        )

        self.assertEqual(payload["title"], "第 1 回：卢沟桥事变快讯发布")
        self.assertTrue(any("1937 年 7 月 7 日" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any("赵川" in dialogue["speaker"] for dialogue in payload["dialogues"]))

    def test_build_scene_story_block_should_fallback_for_unknown_scene(self):
        """未知场景应回退到通用叙事，避免 CLI 因缺文案中断。"""
        payload = build_scene_story_block(
            scenario={
                "id": "SX",
                "title": "未知训练节点",
                "era_date": "1939-01-01",
                "location": "某地",
            },
            player_profile={"name": "李敏"},
            round_no=2,
        )

        self.assertEqual(payload["title"], "第 2 回：未知训练节点")
        self.assertTrue(any("1939-01-01" in paragraph for paragraph in payload["paragraphs"]))
        self.assertEqual(payload["dialogues"], [])

    def test_build_round_feedback_story_block_should_switch_tone_by_risk_flags(self):
        """回合反馈应根据风险标签切换鼓励或提醒语气。"""
        risk_payload = build_round_feedback_story_block(
            scenario={"id": "S3", "title": "南京失守高冲突信息处置"},
            submit_result={
                "evaluation": {
                    "risk_flags": ["source_exposure_risk"],
                    "evidence": ["需要优先保护线人身份"],
                }
            },
            selected_option="A",
        )
        safe_payload = build_round_feedback_story_block(
            scenario={
                "id": "S1",
                "title": "卢沟桥事变快讯发布",
                "decision_focus": "抢发速度与事实核验的平衡",
                "options": [
                    {"id": "C", "label": "先发有限事实并声明仍在核验"},
                ],
            },
            submit_result={"evaluation": {"risk_flags": [], "evidence": ["事实核验比较稳妥"]}},
            selected_option="C",
        )

        self.assertTrue(any("保护" in dialogue["text"] or "危险" in dialogue["text"] for dialogue in risk_payload["dialogues"]))
        self.assertTrue(any("写得稳" in dialogue["text"] for dialogue in safe_payload["dialogues"]))
        self.assertTrue(any("需要优先保护线人身份" in paragraph for paragraph in risk_payload["paragraphs"]))
        self.assertTrue(any("先发有限事实并声明仍在核验" in paragraph for paragraph in safe_payload["paragraphs"]))

    def test_build_transition_story_block_should_connect_known_scene_pairs(self):
        """相邻场景之间应能生成固定转场文案。"""
        payload = build_transition_story_block(
            current_scenario={"id": "S1"},
            next_scenario={"id": "S2"},
            player_profile={"name": "李敏"},
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["title"], "转场")
        self.assertTrue(any("上海" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any("李敏" in dialogue["text"] for dialogue in payload["dialogues"]))

    def test_build_story_epilogue_block_should_include_runtime_ending_type_and_weak_skill(self):
        """终章应兼容当前运行时结局类型并带出短板技能。"""
        payload = build_story_epilogue_block(
            player_profile={"name": "李敏", "identity": "战地记者"},
            report_result={
                "ending": {"ending_type": "史笔如铁"},
                "summary": {
                    "weakest_skill_code": "K3",
                    "strongest_improved_skill_code": "K1",
                    "completed_scenario_ids": ["S1", "S2", "S3", "S4", "S5", "S6"],
                },
            },
        )

        self.assertEqual(payload["title"], "终章：把笔锋写进时代")
        self.assertTrue(any("历史精神" in paragraph or "真实、责任与信念" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any("K3" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any("6 个历史训练关口" in paragraph for paragraph in payload["paragraphs"]))
        self.assertTrue(any(dialogue["speaker"] == "陈编辑" for dialogue in payload["dialogues"]))


if __name__ == "__main__":
    unittest.main()
