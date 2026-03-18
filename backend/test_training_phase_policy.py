"""训练阶段策略测试。"""

from __future__ import annotations

import unittest

from training.config_loader import FlowStageWindowConfig, load_training_runtime_config, model_copy
from training.phase_policy import TrainingPhasePolicy


class TrainingPhasePolicyTestCase(unittest.TestCase):
    """验证训练阶段解析已从推荐逻辑中抽离为独立策略。"""

    def test_should_resolve_default_stage_windows_by_round(self):
        """默认配置下，不同轮次应命中对应阶段标签。"""
        policy = TrainingPhasePolicy()

        opening_phase = policy.resolve_round_phase("guided", round_no=1, total_rounds=6)
        middle_phase = policy.resolve_round_phase("guided", round_no=3, total_rounds=6)
        closing_phase = policy.resolve_round_phase("guided", round_no=6, total_rounds=6)

        self.assertEqual(opening_phase.phase_tags, ["opening"])
        self.assertEqual(middle_phase.phase_tags, ["middle"])
        self.assertEqual(closing_phase.phase_tags, ["closing"])

    def test_should_respect_mode_specific_stage_window(self):
        """阶段窗口如果限定了模式，不应错误作用到其他训练模式。"""
        runtime_config = model_copy(load_training_runtime_config())
        runtime_config.flow.stage_windows = [
            FlowStageWindowConfig(
                start_round=1,
                end_round=1,
                phase_tags=["adaptive_opening"],
                modes=["adaptive"],
                reason="只给 adaptive 使用",
            )
        ]
        policy = TrainingPhasePolicy(runtime_config=runtime_config)

        adaptive_phase = policy.resolve_round_phase("adaptive", round_no=1, total_rounds=3)
        guided_phase = policy.resolve_round_phase("guided", round_no=1, total_rounds=3)

        self.assertEqual(adaptive_phase.phase_tags, ["adaptive_opening"])
        self.assertEqual(guided_phase.phase_tags, [])

    def test_next_round_phase_should_follow_current_round_progress(self):
        """下一轮阶段解析应基于已完成轮次自动换算。"""
        policy = TrainingPhasePolicy()

        next_phase = policy.resolve_next_round_phase(
            training_mode="guided",
            current_round_no=2,
            total_rounds=6,
        )

        self.assertEqual(next_phase.round_no, 3)
        self.assertEqual(next_phase.phase_tags, ["middle"])


if __name__ == "__main__":
    unittest.main()
