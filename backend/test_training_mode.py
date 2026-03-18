"""训练模式规范化测试。"""

from __future__ import annotations

import unittest

from training.training_mode import TrainingModeCatalog


class TrainingModeCatalogTestCase(unittest.TestCase):
    """验证训练模式别名、校验和推荐模式判定。"""

    def setUp(self):
        self.catalog = TrainingModeCatalog()

    def test_normalize_should_canonicalize_aliases(self):
        """下划线和空格写法都应归一成 canonical 模式。"""
        self.assertEqual(self.catalog.normalize("guided"), "guided")
        self.assertEqual(self.catalog.normalize("self_paced"), "self-paced")
        self.assertEqual(self.catalog.normalize("self paced"), "self-paced")
        self.assertEqual(self.catalog.normalize("ADAPTIVE"), "adaptive")

    def test_normalize_should_reject_unknown_mode(self):
        """未知模式应明确报错，而不是静默降级。"""
        with self.assertRaises(ValueError):
            self.catalog.normalize("sandbox")

    def test_catalog_should_resolve_recommendation_and_strict_modes(self):
        """推荐模式和严格模式判断都应基于 canonical 结果。"""
        self.assertTrue(self.catalog.is_recommendation_mode("self_paced"))
        self.assertTrue(self.catalog.is_recommendation_mode("adaptive"))
        self.assertFalse(self.catalog.is_recommendation_mode("guided"))
        self.assertTrue(self.catalog.is_strict_mode("adaptive"))
        self.assertFalse(self.catalog.is_strict_mode("self_paced"))


if __name__ == "__main__":
    unittest.main()
