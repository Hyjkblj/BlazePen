"""训练包导出入口测试。

这一组测试用于防止后续继续拆分 policy 时，遗漏 `training.__init__`
里的稳定导出，导致 `from training import ...` 的调用方被无意义打断。
"""

from __future__ import annotations

import unittest

import training


class TrainingPackageExportsTestCase(unittest.TestCase):
    """校验训练包级导出是否覆盖稳定可注入策略。"""

    def test_training_package_should_export_stable_injectable_policies(self):
        """可注入策略一旦被外部依赖，就应保持对称的包级导出。"""
        expected_exports = [
            "TrainingDecisionContextPolicy",
            "TrainingReportContextPolicy",
            "TrainingRuntimeArtifactPolicy",
            "TrainingOutputAssemblerPolicy",
            "TrainingRoundTransitionPolicy",
            "SessionScenarioSnapshotPolicy",
        ]

        for export_name in expected_exports:
            self.assertTrue(
                hasattr(training, export_name),
                msg=f"missing training package export: {export_name}",
            )


if __name__ == "__main__":
    unittest.main()
