"""训练分支解析器单元测试。"""

from __future__ import annotations

import unittest

from training.branch_resolver import BranchResolver
from training.scenario_repository import ScenarioRepository


class BranchResolverTestCase(unittest.TestCase):
    """验证分支解析器能够基于运行时状态命中正确场景。"""

    def setUp(self):
        self.repository = ScenarioRepository()
        self.resolver = BranchResolver(scenario_repository=self.repository)
        # 主线快照仍只保留主线顺序，分支目录单独冻结到 catalog 里。
        self.mainline_sequence = self.repository.freeze_sequence(
            [
                {"id": "S1", "title": "卢沟桥"},
                {"id": "S2", "title": "淞沪"},
                {"id": "S3", "title": "南京"},
                {"id": "S4", "title": "武汉"},
            ]
        )
        self.scenario_catalog = self.repository.freeze_related_catalog(self.mainline_sequence)

    def test_should_resolve_failure_branch_from_session_catalog_when_flag_matches(self):
        """命中恐慌标记后，应直接从会话冻结目录解析失败分支。"""
        resolution = self.resolver.resolve_next_branch(
            current_scenario_id="S1",
            training_mode="guided",
            runtime_flags={"panic_triggered": True, "source_exposed": True},
            scenario_payload_sequence=self.mainline_sequence,
            scenario_payload_catalog=self.scenario_catalog,
        )

        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.target_scenario_id, "S2B")
        self.assertEqual(resolution.transition_type, "failure_branch")
        self.assertEqual(resolution.scenario["branch_transition"]["source_scenario_id"], "S1")
        self.assertEqual(resolution.scenario["branch_transition"]["target_scenario_id"], "S2B")
        self.assertEqual(resolution.triggered_flags, ["panic_triggered"])

    def test_should_resolve_recovery_branch_before_default_rule(self):
        """恐慌已恢复时，应优先进入补救分支，且不伪造触发 flags。"""
        resolution = self.resolver.resolve_next_branch(
            current_scenario_id="S2B",
            training_mode="guided",
            runtime_flags={"panic_triggered": False},
            scenario_payload_sequence=self.mainline_sequence,
            scenario_payload_catalog=self.scenario_catalog,
        )

        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.target_scenario_id, "S3R")
        self.assertEqual(resolution.transition_type, "recovery_branch")
        self.assertEqual(resolution.scenario["branch_transition"]["source_scenario_id"], "S2B")
        self.assertEqual(resolution.triggered_flags, [])

    def test_should_use_default_return_when_recovery_condition_not_met(self):
        """恢复条件不满足时，应回到默认主线节点，且 default 不应伪造触发 flags。"""
        resolution = self.resolver.resolve_next_branch(
            current_scenario_id="S2B",
            training_mode="guided",
            runtime_flags={"panic_triggered": True},
            scenario_payload_sequence=self.mainline_sequence,
            scenario_payload_catalog=self.scenario_catalog,
        )

        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.target_scenario_id, "S3")
        self.assertEqual(resolution.transition_type, "mainline_return")
        self.assertEqual(resolution.triggered_flags, [])

    def test_should_respect_mode_filter_on_branch_rule(self):
        """分支规则配置了模式限制时，只应在匹配模式下生效。"""
        custom_sequence = [
            {
                "id": "X1",
                "title": "自定义起点",
                "next_rules": [
                    {
                        "go_to": "X2",
                        "default": True,
                        "transition_type": "branch",
                        "modes": ["self-paced"],
                    }
                ],
            },
            {
                "id": "X2",
                "title": "自定义分支",
            },
        ]

        guided_resolution = self.resolver.resolve_next_branch(
            current_scenario_id="X1",
            training_mode="guided",
            runtime_flags={},
            scenario_payload_sequence=custom_sequence,
            scenario_payload_catalog=custom_sequence,
        )
        self.assertIsNone(guided_resolution)

        self_paced_resolution = self.resolver.resolve_next_branch(
            current_scenario_id="X1",
            training_mode="self-paced",
            runtime_flags={},
            scenario_payload_sequence=custom_sequence,
            scenario_payload_catalog=custom_sequence,
        )
        self.assertIsNotNone(self_paced_resolution)
        self.assertEqual(self_paced_resolution.target_scenario_id, "X2")


if __name__ == "__main__":
    unittest.main()
