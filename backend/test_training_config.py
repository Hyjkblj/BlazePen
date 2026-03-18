"""训练运行时配置加载测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from training.config_loader import (
    FlowForcedRoundConfig,
    FlowStageWindowConfig,
    load_training_runtime_config,
    model_to_dict,
)


class TrainingRuntimeConfigTestCase(unittest.TestCase):
    """验证业务规则已从代码迁移到外部配置文件。"""

    def test_should_load_default_runtime_config(self):
        """默认配置文件应能被正常加载并包含核心业务规则。"""
        config = load_training_runtime_config()

        self.assertGreaterEqual(len(config.scenario.default_sequence), 1)
        self.assertIn("verify", {rule.id for rule in config.rule_engine.rules})
        self.assertEqual(config.ending.types.excellent, "史笔如铁")
        self.assertGreaterEqual(config.recommendation.recent_risk_window, 1)
        self.assertGreaterEqual(len(config.recommendation.risk_boosts), 1)
        self.assertGreaterEqual(len(config.recommendation.phase_boosts), 1)
        self.assertIsNotNone(config.flow)
        self.assertGreaterEqual(len(config.flow.stage_windows), 1)
        self.assertGreater(config.reporting.thresholds.weak_skill_threshold, 0.0)
        self.assertGreaterEqual(config.reporting.max_review_suggestions, 1)

    def test_custom_config_file_should_override_business_rules(self):
        """自定义配置文件应能覆盖场景序列与规则参数。"""
        default_config = load_training_runtime_config()
        payload = model_to_dict(default_config)
        payload["scenario"]["version"] = "training_scenario_test_v2"
        payload["scenario"]["default_sequence"] = [{"id": "SX", "title": "自定义场景"}]
        payload["rule_engine"]["rules"][0]["keywords"] = ["定制核验"]
        payload["flow"]["forced_rounds"] = [
            model_to_dict(
                FlowForcedRoundConfig(
                    round_no=2,
                    scenario_id="SX",
                    modes=["self-paced"],
                    reason="测试关键节点",
                )
            )
        ]
        payload["flow"]["stage_windows"] = [
            model_to_dict(
                FlowStageWindowConfig(
                    start_round=1,
                    end_round=1,
                    phase_tags=["opening"],
                    reason="测试阶段窗口",
                )
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "training_runtime_config.json"
            config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            custom_config = load_training_runtime_config(config_path)

        self.assertEqual(custom_config.scenario.version, "training_scenario_test_v2")
        self.assertEqual(custom_config.scenario.default_sequence[0].id, "SX")
        self.assertEqual(custom_config.rule_engine.rules[0].keywords, ["定制核验"])
        self.assertEqual(custom_config.flow.forced_rounds[0].round_no, 2)
        self.assertEqual(custom_config.flow.forced_rounds[0].scenario_id, "SX")
        self.assertEqual(custom_config.flow.stage_windows[0].phase_tags, ["opening"])

    def test_invalid_numeric_config_should_fail_fast(self):
        """关键轮次和推荐窗口等数值配置非法时，应在加载期直接失败。"""
        default_config = load_training_runtime_config()
        payload = model_to_dict(default_config)
        payload["recommendation"]["candidate_limit"] = 0
        payload["recommendation"]["phase_boosts"][0]["distance"] = -1
        payload["flow"]["forced_rounds"] = [
            {
                "round_no": 0,
                "scenario_id": "S1",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "training_runtime_config.json"
            config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_training_runtime_config(config_path)

    def test_conflicting_forced_round_rules_should_fail_fast(self):
        """同一轮次同一模式如果配置了多条关键节点规则，应在加载期直接拦截。"""
        default_config = load_training_runtime_config()
        payload = model_to_dict(default_config)
        payload["flow"]["forced_rounds"] = [
            {
                "round_no": 2,
                "scenario_id": "S2",
                "modes": ["self-paced"],
            },
            {
                "round_no": 2,
                "scenario_id": "S3",
                "modes": ["self_paced"],
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "training_runtime_config.json"
            config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_training_runtime_config(config_path)

    def test_invalid_phase_boost_mapping_should_fail_fast(self):
        """阶段加权配置如果写成半截规则或混搭规则，应在加载期直接失败。"""
        default_config = load_training_runtime_config()
        payload = model_to_dict(default_config)
        payload["recommendation"]["phase_boosts"] = [
            {
                "current_phase_tags": ["opening"],
                "boost": 1.0,
                "reason": "缺少目标阶段标签",
            }
        ]
        payload["flow"]["stage_windows"] = [
            {
                "start_round": 2,
                "end_round": 1,
                "phase_tags": ["opening"],
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "training_runtime_config.json"
            config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_training_runtime_config(config_path)


if __name__ == "__main__":
    unittest.main()
