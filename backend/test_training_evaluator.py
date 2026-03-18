"""训练评估器 P2 流程测试。"""

import unittest

from training.constants import DEFAULT_K_STATE, S_STATE_CODES
from training.evaluator import TrainingRoundEvaluator


class _FakeResponse:
    """模拟 LLM 响应对象，只保留评估器真正会访问的字段。"""

    def __init__(self, text: str, model: str = "mock-model"):
        self.text = text
        self.model = model


class _FakeLLMService:
    """模拟 LLM 服务，隔离真实网络请求。"""

    def __init__(self, text: str, model: str = "mock-model", should_raise: bool = False):
        self._text = text
        self._model = model
        self._should_raise = should_raise

    def call_with_retry(self, **kwargs):
        # 用异常模拟 provider 失败，验证规则回退分支。
        if self._should_raise:
            raise RuntimeError("mock llm failure")
        return _FakeResponse(self._text, self._model)

    def get_model(self):
        return self._model

    def get_provider(self):
        return "mock"


class TrainingRoundEvaluatorTestCase(unittest.TestCase):
    def setUp(self):
        # 使用稳定的基线状态，避免测试受到外部环境影响。
        self.k_before = dict(DEFAULT_K_STATE)
        self.s_before = {key: 0.5 for key in S_STATE_CODES}

    def test_rules_only_mode(self):
        """LLM 关闭时，应固定走 rules_only。"""
        evaluator = TrainingRoundEvaluator(use_llm=False)
        result = evaluator.evaluate_round(
            user_input="未经核实就立即发布全部内容",
            scenario_id="S1",
            round_no=1,
            k_before=self.k_before,
            s_before=self.s_before,
        )

        self.assertEqual(result["eval_mode"], "rules_only")
        self.assertEqual(result["llm_model"], "rules_v1")
        self.assertIn("high_risk_unverified_publish", result["risk_flags"])
        self.assertLess(result["skill_delta"]["K1"], 0.0)
        self.assertIn("skill_scores_preview", result)
        self.assertEqual(len(result["skill_scores_preview"]), len(DEFAULT_K_STATE))

    def test_llm_plus_rules_with_calibration(self):
        """LLM 成功返回结构化 JSON 时，应进入融合与校准链路。"""
        llm_json = """
        {
          "confidence": 0.91,
          "risk_flags": ["source_exposure_risk"],
          "skill_delta": {
            "K1": 0.03, "K2": 0.02, "K3": 0.01, "K4": 0.01,
            "K5": -0.02, "K6": 0.02, "K7": 0.00, "K8": 0.00
          },
          "s_delta": {
            "credibility": 0.01, "accuracy": 0.02, "public_panic": 0.00,
            "source_safety": -0.01, "editor_trust": 0.02, "actionability": 0.01
          },
          "evidence": ["contains source identity hint"]
        }
        """
        evaluator = TrainingRoundEvaluator(use_llm=True, llm_service=_FakeLLMService(text=llm_json))
        result = evaluator.evaluate_round(
            user_input="我想公开线人的真实姓名和具体地址",
            scenario_id="S2",
            round_no=2,
            k_before=self.k_before,
            s_before=self.s_before,
        )

        self.assertEqual(result["eval_mode"], "llm_plus_rules")
        self.assertEqual(result["llm_model"], "mock-model")
        self.assertIn("calibration", result)
        self.assertIn("source_exposure_risk", result["risk_flags"])
        self.assertLessEqual(result["s_delta"]["source_safety"], 0.0)

    def test_llm_parse_failure_fallback(self):
        """LLM 返回不可解析文本时，应回退为 rules_fallback。"""
        evaluator = TrainingRoundEvaluator(use_llm=True, llm_service=_FakeLLMService(text="not-a-json-response"))
        result = evaluator.evaluate_round(
            user_input="我会先核实再发布",
            scenario_id="S3",
            round_no=3,
            k_before=self.k_before,
            s_before=self.s_before,
        )

        self.assertEqual(result["eval_mode"], "rules_fallback")
        self.assertEqual(result["llm_model"], "rules_v1")
        self.assertIn("fallback_reason", result)
        self.assertGreaterEqual(result["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
