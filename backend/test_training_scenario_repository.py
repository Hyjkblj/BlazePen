"""训练场景库加载与冻结测试。"""

from __future__ import annotations

import unittest

from training.scenario_repository import ScenarioRepository


class ScenarioRepositoryTestCase(unittest.TestCase):
    """验证场景库已从服务层中解耦出来。"""

    def setUp(self):
        self.repository = ScenarioRepository()

    def test_should_load_complete_scenario_definition(self):
        """按场景 ID 应该能取到完整场景定义。"""
        scenario = self.repository.get_scenario("S1")

        self.assertIsNotNone(scenario)
        self.assertEqual(scenario["id"], "S1")
        self.assertTrue(len(scenario["options"]) >= 1)
        self.assertTrue(len(scenario["target_skills"]) >= 1)

    def test_freeze_sequence_should_merge_summary_and_full_payload(self):
        """冻结场景序列时，应保留摘要覆盖并补齐完整内容。"""
        frozen = self.repository.freeze_sequence([{"id": "S1", "title": "自定义标题"}])

        self.assertEqual(len(frozen), 1)
        self.assertEqual(frozen[0]["id"], "S1")
        self.assertEqual(frozen[0]["title"], "自定义标题")
        self.assertIn("briefing", frozen[0])
        self.assertIn("options", frozen[0])


if __name__ == "__main__":
    unittest.main()
