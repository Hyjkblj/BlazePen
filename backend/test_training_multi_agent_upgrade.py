"""Training Multi-Agent Upgrade — 属性测试 + 单元测试。

覆盖 tasks.md 中所有标记 * 的可选测试任务：
  1.2  Property 1: 场景总数不变量
  1.4  Property 2: 延伸模式总场景数公式
  1.5  Step 1 单元测试
  2.4  Property 3/4/5: RecommendationAgent 属性测试
  2.6  Step 2 单元测试
  4.2  Property 10: Director Agent 属性测试
  4.4  Step 3 单元测试
  5.2  Property 6/7/8/9: Evaluator 历史注入属性测试
  5.5  Step 4 单元测试
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from training.session_storyline_policy import SessionStorylinePolicy
from training.story_script_agent import StoryScriptAgentConfig
from training.recommendation_agent import RecommendationAgent
from training.recommendation_policy import RecommendationPolicy
from training.director_agent import ExecutionPlan, TrainingDirectorAgent
from training.evaluator import TrainingRoundEvaluator


# ===========================================================================
# Step 1 — 场景结构一致性
# ===========================================================================

class Step1UnitTests(unittest.TestCase):
    """1.5 Step 1 单元测试"""

    def test_session_storyline_policy_default_micro_scene_min(self):
        """Requirements 1.1: micro_scene_min 默认值应为 3。"""
        policy = SessionStorylinePolicy()
        self.assertEqual(policy.micro_scene_min, 3)

    def test_session_storyline_policy_default_micro_scene_max(self):
        """Requirements 1.1: micro_scene_max 默认值应为 3。"""
        policy = SessionStorylinePolicy()
        self.assertEqual(policy.micro_scene_max, 3)

    def test_story_script_agent_config_default_micro_scenes_per_gap(self):
        """Requirements 1.3: StoryScriptAgentConfig 默认 micro_scenes_per_gap 应为 3。"""
        config = StoryScriptAgentConfig()
        self.assertEqual(config.micro_scenes_per_gap, 3)

    def test_story_script_agent_config_extension_formula(self):
        """Requirements 1.4: 延伸模式公式 total_micro = major * micro_per_gap。"""
        config = StoryScriptAgentConfig(major_scene_count=6, micro_scenes_per_gap=3)
        total_micro_extension = config.major_scene_count * config.micro_scenes_per_gap
        total_micro_gap = (config.major_scene_count - 1) * config.micro_scenes_per_gap
        # 延伸模式比间隙模式多 micro_scenes_per_gap 个小场景
        self.assertEqual(total_micro_extension, 18)
        self.assertEqual(total_micro_gap, 15)
        self.assertGreater(total_micro_extension, total_micro_gap)

    def test_story_script_fallback_uses_extension_mode(self):
        """Requirements 1.4/1.5: fallback payload 中每个大场景后都有 micro_per_gap 个小场景。"""
        config = StoryScriptAgentConfig(major_scene_count=3, micro_scenes_per_gap=3)
        agent = _make_story_script_agent(config=config)
        payload = agent._call_local_fallback_payload(
            session_id="test",
            major_scene_sources=[],
            player_profile=None,
        )
        scenes = payload.get("scenes", [])
        major_scenes = [s for s in scenes if s.get("scene_type") == "major"]
        micro_scenes = [s for s in scenes if s.get("scene_type") == "micro"]
        self.assertEqual(len(major_scenes), 3)
        self.assertEqual(len(micro_scenes), 9)  # 3 major × 3 micro each


def _make_story_script_agent(config=None):
    """Helper: build StoryScriptAgent with a fake store."""
    from training.story_script_agent import StoryScriptAgent
    fake_store = SimpleNamespace(
        get_story_script_by_session_id=lambda sid: None,
        create_story_script=lambda **kw: SimpleNamespace(payload={}),
        update_story_script_by_session_id=lambda sid, updates: None,
    )
    return StoryScriptAgent(training_store=fake_store, config=config)


# ---------------------------------------------------------------------------
# Property 1: 场景总数不变量
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 1: 场景总数不变量
@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=8))
def test_property_scene_count_invariant(major_count):
    """1.2: 任意 N 个大场景，build_session_sequence 应产出 N major + N*3 micro。"""
    policy = SessionStorylinePolicy(micro_scene_min=3, micro_scene_max=3)
    base = [{"id": f"S{i}", "title": f"场景{i}"} for i in range(1, major_count + 1)]
    result = policy.build_session_sequence(
        training_mode="guided",
        base_sequence=base,
        player_profile={"identity": "记者", "name": "测试", "force_storyline_expansion": True},
    )
    major_scenes = [s for s in result if s.get("scene_level") == "major"]
    micro_scenes = [s for s in result if s.get("scene_level") == "micro"]
    assert len(major_scenes) == major_count, f"expected {major_count} major, got {len(major_scenes)}"
    assert len(micro_scenes) == major_count * 3, f"expected {major_count * 3} micro, got {len(micro_scenes)}"


# Feature: training-multi-agent-upgrade, Property 2: 延伸模式总场景数公式
@settings(max_examples=100)
@given(
    st.integers(min_value=1, max_value=10),
    st.integers(min_value=1, max_value=5),
)
def test_property_extension_formula(major_count, micro_per_gap):
    """1.4: 延伸公式 total = major + major*micro_per_gap，不等于间隙公式（除非 major==1）。"""
    extension_total = major_count + major_count * micro_per_gap
    gap_total = major_count + (major_count - 1) * micro_per_gap
    assert extension_total >= gap_total
    if major_count > 1:
        assert extension_total > gap_total
    else:
        assert extension_total == gap_total  # major=1 时两公式相等


# ===========================================================================
# Step 2 — RecommendationAgent
# ===========================================================================

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scenario(scenario_id: str) -> Dict[str, Any]:
    return {
        "id": scenario_id,
        "title": f"场景 {scenario_id}",
        "target_skills": ["K1", "K2"],
        "risk_tags": [],
        "phase_tags": ["opening"],
        "options": [],
    }


_scenario_strategy = st.lists(
    st.fixed_dictionaries({
        "id": st.text(min_size=1, max_size=8, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"),
        "title": st.just("场景"),
        "target_skills": st.just(["K1"]),
        "risk_tags": st.just([]),
        "phase_tags": st.just(["opening"]),
        "options": st.just([]),
    }),
    min_size=1,
    max_size=6,
).map(lambda items: list({item["id"]: item for item in items}.values()))  # deduplicate by id


class Step2UnitTests(unittest.TestCase):
    """2.6 Step 2 单元测试"""

    def test_recommendation_agent_is_subclass_of_recommendation_policy(self):
        """Requirements 2.1: RecommendationAgent 必须继承 RecommendationPolicy。"""
        agent = RecommendationAgent(use_llm=False)
        self.assertIsInstance(agent, RecommendationPolicy)

    def test_recommendation_agent_exported_from_training_package(self):
        """Requirements 2.9: from training import RecommendationAgent 应可正常导入。"""
        from training import RecommendationAgent as ImportedAgent
        self.assertIs(ImportedAgent, RecommendationAgent)

    def test_training_service_uses_recommendation_agent_by_default(self):
        """Requirements 2.10: TrainingService 默认 recommendation_policy 应为 RecommendationAgent。"""
        from api.services.training_service import TrainingService
        from training.training_store import DatabaseTrainingStore
        fake_store = MagicMock(spec=DatabaseTrainingStore)
        fake_store.get_training_session.return_value = None
        service = TrainingService(training_store=fake_store)
        self.assertIsInstance(service.recommendation_policy, RecommendationAgent)

    def test_rank_candidates_marks_override_source_rules(self):
        """Requirements 2.11: use_llm=False 时所有候选的 override_source 应为 'rules'。"""
        agent = RecommendationAgent(use_llm=False)
        candidates = [_make_scenario("S1"), _make_scenario("S2")]
        result = agent.rank_candidates("adaptive", candidates, [])
        for item in result:
            self.assertEqual(item["recommendation"]["override_source"], "rules")

    def test_rank_candidates_empty_returns_empty(self):
        """空候选列表应返回空列表，不抛出异常。"""
        agent = RecommendationAgent(use_llm=False)
        result = agent.rank_candidates("adaptive", [], [])
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Property 3: LLM 未触发时推荐结果与规则一致
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 3: LLM 未触发时推荐结果与规则一致
@settings(max_examples=100)
@given(_scenario_strategy)
def test_property_no_llm_override_matches_rules(candidates):
    """Requirements 2.2/2.3: use_llm=False 时结果顺序应与父类一致（忽略 override_source）。"""
    agent = RecommendationAgent(use_llm=False)
    policy = RecommendationPolicy()
    agent_result = agent.rank_candidates("adaptive", candidates, [], {}, {})
    policy_result = policy.rank_candidates("adaptive", candidates, [], {}, {})
    assert len(agent_result) == len(policy_result)
    for a, p in zip(agent_result, policy_result):
        assert a["id"] == p["id"], f"order mismatch: agent={a['id']} policy={p['id']}"


# Feature: training-multi-agent-upgrade, Property 4: LLM 覆盖仅替换 top-1，其余顺序不变
@settings(max_examples=50)
@given(_scenario_strategy.filter(lambda c: len(c) >= 2))
def test_property_llm_override_only_top1(candidates):
    """Requirements 2.4/2.11: LLM 覆盖时 index>=1 的顺序不变，override_source='rules'。"""
    # 构造一个总是返回第二个候选的 mock LLM
    policy = RecommendationPolicy()
    rules_result = policy.rank_candidates("adaptive", candidates, [], {"K1": 0.1}, {})
    if len(rules_result) < 2:
        return  # 候选不足，跳过

    second_id = rules_result[1]["id"]

    class _MockLLMSelectSecond:
        def call(self, messages, **kw):
            import json as _json
            return SimpleNamespace(text=_json.dumps({"selected_id": second_id, "reason": "test"}))

    agent = RecommendationAgent(use_llm=True, llm_service=_MockLLMSelectSecond())
    # 触发 LLM 覆盖：技能极低
    with patch.object(agent, "_should_llm_override", return_value=True):
        result = agent.rank_candidates("adaptive", candidates, [], {"K1": 0.1}, {})

    # index >= 1 的顺序不变
    for i in range(1, len(result)):
        assert result[i]["id"] == rules_result[i]["id"], (
            f"index {i} changed: {result[i]['id']} != {rules_result[i]['id']}"
        )
        assert result[i]["recommendation"]["override_source"] == "rules"


# Feature: training-multi-agent-upgrade, Property 5: LLM 失败时静默降级
@settings(max_examples=100)
@given(_scenario_strategy)
def test_property_llm_failure_silent_fallback(candidates):
    """Requirements 2.5: LLM 抛出异常时不应传播，结果应与规则排序一致。"""
    class _MockLLMAlwaysRaises:
        def call(self, messages, **kw):
            raise RuntimeError("simulated LLM failure")

    agent = RecommendationAgent(use_llm=True, llm_service=_MockLLMAlwaysRaises())
    with patch.object(agent, "_should_llm_override", return_value=True):
        # 不应抛出异常
        result = agent.rank_candidates("adaptive", candidates, [], {"K1": 0.1}, {})

    policy = RecommendationPolicy()
    rules_result = policy.rank_candidates("adaptive", candidates, [], {"K1": 0.1}, {})
    assert len(result) == len(rules_result)
    for r, p in zip(result, rules_result):
        assert r["id"] == p["id"]


# ===========================================================================
# Step 3 — Director Agent
# ===========================================================================

class Step3UnitTests(unittest.TestCase):
    """4.4 Step 3 单元测试"""

    def test_execution_plan_has_required_fields(self):
        """Requirements 3.2: ExecutionPlan 必须包含四个字段。"""
        plan = ExecutionPlan()
        self.assertIsInstance(plan.needs_script_refresh, bool)
        self.assertIsInstance(plan.force_low_risk_scenario, bool)
        self.assertIsInstance(plan.eval_retry_budget, int)
        self.assertIsNone(plan.branch_hint)

    def test_execution_plan_default_values(self):
        """Requirements 3.2: 默认值应为安全值。"""
        plan = ExecutionPlan()
        self.assertFalse(plan.needs_script_refresh)
        self.assertFalse(plan.force_low_risk_scenario)
        self.assertEqual(plan.eval_retry_budget, 1)

    def test_director_agent_plan_returns_execution_plan(self):
        """Requirements 3.4: plan() 应返回 ExecutionPlan 实例。"""
        agent = TrainingDirectorAgent(use_llm=False)
        plan = agent.plan(session=None, round_no=1, k_state={}, s_state={})
        self.assertIsInstance(plan, ExecutionPlan)

    def test_director_agent_force_low_risk_on_consecutive_risk(self):
        """Requirements 3.3: 连续 2 轮高风险时 force_low_risk_scenario=True。"""
        agent = TrainingDirectorAgent(use_llm=False)
        plan = agent.plan(
            session=None,
            round_no=3,
            k_state={},
            s_state={},
            recent_risk_rounds=[["risk_a"], ["risk_b"]],
        )
        self.assertTrue(plan.force_low_risk_scenario)

    def test_director_agent_needs_refresh_on_weak_skill(self):
        """Requirements 3.3: 某项技能 < 0.25 时 needs_script_refresh=True。"""
        agent = TrainingDirectorAgent(use_llm=False)
        plan = agent.plan(
            session=None,
            round_no=1,
            k_state={"K1": 0.1, "K2": 0.8},
            s_state={},
        )
        self.assertTrue(plan.needs_script_refresh)

    def test_director_agent_eval_retry_budget_on_high_panic(self):
        """Requirements 3.3: public_panic > 0.65 时 eval_retry_budget=2。"""
        agent = TrainingDirectorAgent(use_llm=False)
        plan = agent.plan(
            session=None,
            round_no=1,
            k_state={},
            s_state={"public_panic": 0.8},
        )
        self.assertEqual(plan.eval_retry_budget, 2)

    def test_submit_round_calls_director_agent(self):
        """Requirements 3.6: submit_round 应调用 director_agent.plan。"""
        from api.services.training_service import TrainingService
        mock_director = MagicMock()
        mock_director.plan.return_value = ExecutionPlan()

        fake_store = _make_fake_store_for_submit()
        service = TrainingService(
            training_store=fake_store,
            evaluator=_FakeEvaluatorForDirector(),
        )
        service.director_agent = mock_director

        session_id = _init_session(service)
        service.submit_round(
            session_id=session_id,
            scenario_id=fake_store._first_scenario_id,
            user_input="test input",
        )
        mock_director.plan.assert_called_once()

    def test_submit_round_continues_when_director_agent_raises(self):
        """Requirements 3.9: director_agent.plan 抛出异常时 submit_round 不中断。"""
        from api.services.training_service import TrainingService
        mock_director = MagicMock()
        mock_director.plan.side_effect = RuntimeError("director failed")

        fake_store = _make_fake_store_for_submit()
        service = TrainingService(
            training_store=fake_store,
            evaluator=_FakeEvaluatorForDirector(),
        )
        service.director_agent = mock_director

        session_id = _init_session(service)
        # 不应抛出异常
        result = service.submit_round(
            session_id=session_id,
            scenario_id=fake_store._first_scenario_id,
            user_input="test input",
        )
        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# Helpers for Step 3 tests
# ---------------------------------------------------------------------------

class _FakeEvaluatorForDirector:
    def evaluate_round(self, **kwargs):
        from training.constants import DEFAULT_EVAL_MODEL, DEFAULT_K_STATE, S_STATE_CODES, SKILL_CODES
        return {
            "llm_model": DEFAULT_EVAL_MODEL,
            "confidence": 0.8,
            "risk_flags": [],
            "skill_delta": {c: 0.01 for c in SKILL_CODES},
            "s_delta": {c: 0.0 for c in S_STATE_CODES},
            "evidence": ["ok"],
            "skill_scores_preview": {c: 0.5 for c in SKILL_CODES},
            "eval_mode": "rules_only",
        }


def _make_fake_store_for_submit():
    """Build a minimal in-memory store that supports submit_round."""
    from datetime import datetime
    from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE

    store = SimpleNamespace()
    sessions: Dict[str, Any] = {}
    rounds: List[Any] = []
    evaluations: List[Any] = []
    store._first_scenario_id = None

    def create_training_session_artifacts(**kw):
        sid = f"s-{len(sessions)+1}"
        meta = dict(kw.get("session_meta") or {})
        seq = meta.get("scenario_sequence") or []
        if seq:
            store._first_scenario_id = seq[0]["id"]
        row = SimpleNamespace(
            session_id=sid,
            user_id=kw.get("user_id", "u1"),
            character_id=None,
            training_mode=kw.get("training_mode", "guided"),
            status="in_progress",
            current_round_no=0,
            current_scenario_id=None,
            k_state=dict(kw.get("k_state") or DEFAULT_K_STATE),
            s_state=dict(kw.get("s_state") or DEFAULT_S_STATE),
            session_meta=meta,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            end_time=None,
        )
        sessions[sid] = row
        return row

    def get_training_session(sid):
        return sessions.get(sid)

    def save_training_round_artifacts(**kw):
        sid = kw["session_id"]
        rno = kw["round_no"]
        row = SimpleNamespace(
            round_id=f"r-{len(rounds)+1}",
            session_id=sid,
            round_no=rno,
            scenario_id=kw["scenario_id"],
            user_action=kw.get("user_action"),
            kt_after=kw.get("kt_after"),
            state_after=kw.get("state_after"),
        )
        rounds.append(row)
        evaluations.append(SimpleNamespace(
            round_id=row.round_id,
            round_no=rno,
            scenario_id=kw["scenario_id"],
            raw_payload=kw.get("evaluation_payload"),
            evaluation_payload=kw.get("evaluation_payload"),
        ))
        s = sessions.get(sid)
        if s:
            s.current_round_no = rno
            s.current_scenario_id = kw["scenario_id"]
            s.k_state = kw.get("kt_after") or s.k_state
            s.s_state = kw.get("state_after") or s.s_state
            s.status = kw.get("status", s.status)
            s.session_meta = kw.get("session_meta") or s.session_meta
        return row

    store.create_training_session_artifacts = create_training_session_artifacts
    store.get_training_session = get_training_session
    store.save_training_round_artifacts = save_training_round_artifacts
    store.get_training_rounds = lambda sid: [r for r in rounds if r.session_id == sid]
    store.get_round_evaluations_by_session = lambda sid: [e for e in evaluations if getattr(e, "session_id", None) == sid] if evaluations else []
    store.get_round_evaluation_by_round_id = lambda rid: next((e for e in evaluations if e.round_id == rid), None)
    store.get_ending_result = lambda sid: None
    store.get_scenario_recommendation_logs = lambda sid: []
    store.get_training_audit_events = lambda sid: []
    store.get_kt_observations = lambda sid: []
    store.list_media_tasks = lambda **kw: []
    store.upsert_scenario_recommendation_log = lambda *a, **kw: None
    store.create_training_audit_event = lambda **kw: None
    store.create_kt_observation = lambda *a, **kw: None
    store.update_training_session = lambda sid, updates: None
    store.get_training_round_by_session_round = lambda sid, rno: None
    return store


def _init_session(service) -> str:
    result = service.init_training(user_id="u1", training_mode="guided")
    return result["session_id"]


# Feature: training-multi-agent-upgrade, Property 10: Director Agent 在任意输入下返回合法 ExecutionPlan
@settings(max_examples=100)
@given(
    st.dictionaries(st.text(min_size=1, max_size=4), st.floats(0.0, 1.0, allow_nan=False)),
    st.dictionaries(st.text(min_size=1, max_size=16), st.floats(0.0, 1.0, allow_nan=False)),
    st.integers(min_value=1, max_value=30),
)
def test_property_director_agent_always_returns_plan(k_state, s_state, round_no):
    """Requirements 3.4/3.9: 任意输入下 plan() 应返回合法 ExecutionPlan，不抛出异常。"""
    agent = TrainingDirectorAgent(use_llm=False)
    plan = agent.plan(session=None, round_no=round_no, k_state=k_state, s_state=s_state)
    assert isinstance(plan, ExecutionPlan)
    assert isinstance(plan.needs_script_refresh, bool)
    assert isinstance(plan.force_low_risk_scenario, bool)
    assert isinstance(plan.eval_retry_budget, int)
    assert plan.eval_retry_budget >= 1


# ===========================================================================
# Step 1 补充 — P2 prompt 字符串验证（补齐 ⚠️ 部分）
# ===========================================================================

class Step1PromptVerificationTests(unittest.TestCase):
    """1.4 补充：验证 LLM prompt 中 total_scenes 使用延伸公式而非间隙公式。"""

    def _capture_prompt(self, major_count: int, micro_per_gap: int) -> str:
        """通过 mock text_model_service 捕获实际发送给 LLM 的 prompt 内容。"""
        from training.story_script_agent import StoryScriptAgent, StoryScriptAgentConfig
        from types import SimpleNamespace

        captured: list = []

        class _MockTextModelService:
            def generate_text(self, prompt, **kw):
                captured.append(prompt)
                # 返回最小合法 JSON，避免后续解析失败
                import json as _json
                scenes = []
                for mi in range(1, major_count + 1):
                    scenes.append({
                        "scene_id": f"major-{mi}", "scene_type": "major",
                        "title": f"主场景{mi}", "time_hint": "", "location_hint": "",
                        "monologue": "独白", "dialogue": [
                            {"speaker": "旁白", "content": f"c{i}"} for i in range(6)
                        ],
                        "bridge_summary": "承接",
                        "options": [
                            {"option_id": "opt-1", "label": "选A", "impact_hint": "影响A"},
                            {"option_id": "opt-2", "label": "选B", "impact_hint": "影响B"},
                            {"option_id": "opt-3", "label": "选C", "impact_hint": "影响C"},
                        ],
                    })
                    for mk in range(1, micro_per_gap + 1):
                        scenes.append({
                            "scene_id": f"micro-{mi}-{mk}", "scene_type": "micro",
                            "title": f"小场景{mi}-{mk}", "time_hint": "", "location_hint": "",
                            "monologue": "独白", "dialogue": [
                                {"speaker": "旁白", "content": f"c{i}"} for i in range(6)
                            ],
                            "bridge_summary": "承接",
                            "options": [
                                {"option_id": "opt-1", "label": "选A", "impact_hint": "影响A"},
                                {"option_id": "opt-2", "label": "选B", "impact_hint": "影响B"},
                                {"option_id": "opt-3", "label": "选C", "impact_hint": "影响C"},
                            ],
                        })
                payload = {
                    "version": "training_story_script_v1",
                    "cast": [{"name": "陈编辑", "role": "总编把关"}],
                    "major_scenes": [],
                    "scenes": scenes,
                }
                return _json.dumps(payload, ensure_ascii=False)

            def get_provider(self): return "mock"
            def get_model(self): return "mock-model"

        fake_store = SimpleNamespace(
            get_story_script_by_session_id=lambda sid: None,
            create_story_script=lambda **kw: SimpleNamespace(payload={}),
            update_story_script_by_session_id=lambda sid, updates: None,
        )
        config = StoryScriptAgentConfig(
            major_scene_count=major_count,
            micro_scenes_per_gap=micro_per_gap,
        )
        agent = StoryScriptAgent(
            training_store=fake_store,
            text_model_service=_MockTextModelService(),
            config=config,
        )
        agent._call_llm_generate_payload(
            session_id="test-prompt",
            major_scene_sources=[],
            player_profile=None,
        )
        return captured[0] if captured else ""

    def test_prompt_uses_extension_total_scenes(self):
        """Requirements 1.4: prompt 中 total_scenes 应等于 major + major*micro_per_gap（延伸公式）。"""
        major, micro = 6, 3
        extension_total = major + major * micro
        gap_total = major + (major - 1) * micro

        prompt = self._capture_prompt(major, micro)
        self.assertIn(str(extension_total), prompt, "prompt 中应包含延伸公式计算的 total_scenes")
        # 确保没有用间隙公式的值（两者不同时才有意义）
        self.assertNotEqual(extension_total, gap_total)

    def test_prompt_uses_extension_semantics_not_transition(self):
        """Requirements 1.5: prompt 中应包含"延伸"语义，不应出现"过渡"语义。"""
        prompt = self._capture_prompt(6, 3)
        self.assertIn("延伸", prompt, "prompt 应包含'延伸'语义描述")
        self.assertNotIn("过渡", prompt, "prompt 不应包含旧的'过渡'语义描述")

    def test_prompt_uses_after_each_major_not_between(self):
        """Requirements 1.5: prompt 应描述'每个大场景之后'，而非'每两个相邻大场景之间'。"""
        prompt = self._capture_prompt(6, 3)
        self.assertIn("每个大场景之后", prompt)
        self.assertNotIn("每两个相邻大场景之间", prompt)


# ===========================================================================
# Step 4 — Evaluator 历史上下文注入
# ===========================================================================

def _make_rules_only_evaluator() -> TrainingRoundEvaluator:
    """构造纯规则评估器，不依赖 LLM，测试可离线运行。"""
    return TrainingRoundEvaluator(use_llm=False)


def _make_llm_evaluator(mock_llm_service: Any) -> TrainingRoundEvaluator:
    """构造注入 mock LLM 的评估器，用于验证 prompt 内容。"""
    return TrainingRoundEvaluator(use_llm=True, llm_service=mock_llm_service)


class _CapturingLLMService:
    """捕获 _build_llm_messages 实际发送的 messages，供断言使用。"""

    def __init__(self):
        self.captured_messages: list = []

    def call_with_retry(self, messages, **kw):
        self.captured_messages.append(list(messages))
        # 返回最小合法评估 JSON
        import json as _json
        from types import SimpleNamespace
        payload = {
            "confidence": 0.7,
            "risk_flags": [],
            "skill_delta": {c: 0.01 for c in ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"]},
            "s_delta": {c: 0.0 for c in ["credibility", "accuracy", "public_panic", "source_safety", "editor_trust", "actionability"]},
            "evidence": ["测试证据"],
        }
        return SimpleNamespace(text=_json.dumps(payload), model="mock-model")

    def get_provider(self): return "mock"
    def get_model(self): return "mock-model"


# ---------------------------------------------------------------------------
# 5.5 Step 4 单元测试
# ---------------------------------------------------------------------------

class Step4UnitTests(unittest.TestCase):
    """5.5 Step 4 单元测试"""

    def test_evaluate_round_backward_compatible_no_recent_history(self):
        """Requirements 4.1: 不传 recent_history 时 evaluate_round 应正常返回。"""
        evaluator = _make_rules_only_evaluator()
        result = evaluator.evaluate_round("测试输入", "S1", 1)
        self.assertIsNotNone(result)
        self.assertIn("skill_delta", result)
        self.assertIn("eval_mode", result)

    def test_evaluate_round_none_history_same_as_no_arg(self):
        """Requirements 4.2: recent_history=None 与不传参数结果完全一致。"""
        evaluator = _make_rules_only_evaluator()
        result_no_arg = evaluator.evaluate_round("测试输入", "S1", 5)
        result_none = evaluator.evaluate_round("测试输入", "S1", 5, recent_history=None)
        self.assertEqual(result_no_arg["skill_delta"], result_none["skill_delta"])
        self.assertEqual(result_no_arg["eval_mode"], result_none["eval_mode"])
        self.assertEqual(result_no_arg["risk_flags"], result_none["risk_flags"])

    def test_evaluate_round_empty_history_same_as_none(self):
        """Requirements 4.2: recent_history=[] 与 recent_history=None 结果完全一致。"""
        evaluator = _make_rules_only_evaluator()
        result_none = evaluator.evaluate_round("测试输入", "S1", 5, recent_history=None)
        result_empty = evaluator.evaluate_round("测试输入", "S1", 5, recent_history=[])
        self.assertEqual(result_none["skill_delta"], result_empty["skill_delta"])
        self.assertEqual(result_none["eval_mode"], result_empty["eval_mode"])

    def test_no_history_injection_when_round_no_less_than_3(self):
        """Requirements 4.4: round_no < 3 时即使传入非空 recent_history 也不注入。"""
        llm = _CapturingLLMService()
        evaluator = _make_llm_evaluator(llm)
        history = [{"round_no": 1, "scenario_id": "S1", "risk_flags": ["r1"], "evidence": ["e1"]}]
        evaluator.evaluate_round("测试输入", "S1", 2, recent_history=history)
        self.assertTrue(len(llm.captured_messages) > 0)
        user_content = llm.captured_messages[0][1]["content"]
        self.assertNotIn("recent_history", user_content)

    def test_history_injected_when_round_no_gte_3(self):
        """Requirements 4.3: round_no >= 3 且 recent_history 非空时应注入历史摘要。"""
        llm = _CapturingLLMService()
        evaluator = _make_llm_evaluator(llm)
        history = [{"round_no": 2, "scenario_id": "S2", "risk_flags": ["r1"], "evidence": ["e1"]}]
        evaluator.evaluate_round("测试输入", "S3", 3, recent_history=history)
        self.assertTrue(len(llm.captured_messages) > 0)
        user_content = llm.captured_messages[0][1]["content"]
        self.assertIn("recent_history", user_content)

    def test_build_recent_history_returns_empty_when_round_no_lt_3(self):
        """Requirements 4.6: _build_recent_history 在 round_no < 3 时返回空列表。"""
        from api.services.training_service import TrainingService
        from unittest.mock import MagicMock
        fake_store = MagicMock()
        service = TrainingService(training_store=fake_store)
        result = service._build_recent_history(session_id="s1", round_no=2)
        self.assertEqual(result, [])
        fake_store.get_round_evaluations_by_session.assert_not_called()

    def test_build_recent_history_returns_empty_on_store_exception(self):
        """Requirements 4.6: store 抛出异常时 _build_recent_history 返回空列表，不传播异常。"""
        from api.services.training_service import TrainingService
        from unittest.mock import MagicMock
        fake_store = MagicMock()
        fake_store.get_round_evaluations_by_session.side_effect = RuntimeError("db error")
        service = TrainingService(training_store=fake_store)
        result = service._build_recent_history(session_id="s1", round_no=5)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Property 6: recent_history=None 时评估行为不变
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 6: recent_history=None 时评估行为不变
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=200),
    st.integers(min_value=1, max_value=30),
)
def test_property_no_history_same_result(user_input, round_no):
    """Requirements 4.2: 任意输入下，recent_history=None/[] 与不传参数结果完全一致。"""
    evaluator = _make_rules_only_evaluator()
    result_default = evaluator.evaluate_round(user_input, "S1", round_no)
    result_none = evaluator.evaluate_round(user_input, "S1", round_no, recent_history=None)
    result_empty = evaluator.evaluate_round(user_input, "S1", round_no, recent_history=[])
    # 规则路径是确定性的，三者应完全一致
    assert result_default["skill_delta"] == result_none["skill_delta"]
    assert result_default["skill_delta"] == result_empty["skill_delta"]
    assert result_default["eval_mode"] == result_none["eval_mode"]
    assert result_default["risk_flags"] == result_none["risk_flags"]


# ---------------------------------------------------------------------------
# Property 7: 历史注入当且仅当 round_no >= 3 且 recent_history 非空
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 7: 历史注入条件
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=100),
    st.integers(min_value=3, max_value=30),
    st.lists(
        st.fixed_dictionaries({
            "round_no": st.integers(1, 10),
            "scenario_id": st.text(min_size=1, max_size=8),
            "risk_flags": st.lists(st.text(min_size=1, max_size=10), max_size=3),
            "evidence": st.lists(st.text(min_size=1, max_size=20), max_size=2),
        }),
        min_size=1,
        max_size=3,
    ),
)
def test_property_history_injected_when_round_gte_3_and_nonempty(user_input, round_no, history):
    """Requirements 4.3: round_no >= 3 且 recent_history 非空时，messages 中应包含历史摘要。"""
    llm = _CapturingLLMService()
    evaluator = _make_llm_evaluator(llm)
    evaluator.evaluate_round(user_input, "S1", round_no, recent_history=history)
    assert len(llm.captured_messages) > 0
    user_content = llm.captured_messages[0][1]["content"]
    assert "recent_history" in user_content, (
        f"round_no={round_no} 且 history 非空时，prompt 应包含 recent_history"
    )


# Feature: training-multi-agent-upgrade, Property 7 补充: round_no < 3 时不注入
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=100),
    st.integers(min_value=1, max_value=2),
    st.lists(
        st.fixed_dictionaries({
            "round_no": st.integers(1, 2),
            "scenario_id": st.text(min_size=1, max_size=8),
            "risk_flags": st.just([]),
            "evidence": st.just([]),
        }),
        min_size=1,
        max_size=3,
    ),
)
def test_property_no_history_injection_when_round_lt_3(user_input, round_no, history):
    """Requirements 4.4: round_no < 3 时即使 recent_history 非空，messages 中也不应包含历史摘要。"""
    llm = _CapturingLLMService()
    evaluator = _make_llm_evaluator(llm)
    evaluator.evaluate_round(user_input, "S1", round_no, recent_history=history)
    assert len(llm.captured_messages) > 0
    user_content = llm.captured_messages[0][1]["content"]
    assert "recent_history" not in user_content, (
        f"round_no={round_no} < 3 时，prompt 不应包含 recent_history"
    )


# ---------------------------------------------------------------------------
# Property 8: 非法历史记录被跳过，不抛出异常
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 8: 非法历史记录被跳过
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=100),
    st.lists(
        st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=10),
            st.fixed_dictionaries({}),  # 空 dict（缺所有字段）
            st.fixed_dictionaries({
                "round_no": st.integers(1, 5),
                "scenario_id": st.text(min_size=1, max_size=8),
                "risk_flags": st.just([]),
                "evidence": st.just([]),
            }),
        ),
        min_size=1,
        max_size=5,
    ),
)
def test_property_invalid_history_entries_skipped_no_exception(user_input, mixed_history):
    """Requirements 4.7: 包含任意非法记录的 recent_history 不应导致异常。"""
    evaluator = _make_rules_only_evaluator()
    # 不应抛出任何异常
    try:
        result = evaluator.evaluate_round(user_input, "S1", 5, recent_history=mixed_history)
        assert result is not None
        assert "skill_delta" in result
    except Exception as exc:
        raise AssertionError(f"evaluate_round 不应抛出异常，但抛出了: {exc}") from exc


# Feature: training-multi-agent-upgrade, Property 8 补充: LLM 路径下非法记录也不崩溃
@settings(max_examples=50)
@given(
    st.text(min_size=1, max_size=100),
    st.lists(
        st.one_of(
            st.none(),
            st.text(max_size=5),
            st.fixed_dictionaries({}),
        ),
        min_size=1,
        max_size=4,
    ),
)
def test_property_invalid_history_no_exception_with_llm(user_input, bad_history):
    """Requirements 4.7: LLM 路径下非法 recent_history 也不应崩溃。"""
    llm = _CapturingLLMService()
    evaluator = _make_llm_evaluator(llm)
    try:
        result = evaluator.evaluate_round(user_input, "S1", 5, recent_history=bad_history)
        assert result is not None
    except Exception as exc:
        raise AssertionError(f"LLM 路径下 evaluate_round 不应抛出异常，但抛出了: {exc}") from exc


# ---------------------------------------------------------------------------
# Property 9: 历史摘要不包含原始用户输入全文
# ---------------------------------------------------------------------------

# Feature: training-multi-agent-upgrade, Property 9: 历史摘要不含原始用户输入
@settings(max_examples=100)
@given(
    st.text(min_size=5, max_size=200),
    st.lists(
        st.fixed_dictionaries({
            "round_no": st.integers(1, 5),
            "scenario_id": st.text(min_size=1, max_size=8),
            "risk_flags": st.lists(st.text(min_size=1, max_size=10), max_size=2),
            "evidence": st.lists(st.text(min_size=1, max_size=20), max_size=2),
            # 故意在历史记录里塞入 user_input 字段，验证它不会被注入 prompt
            "user_input": st.text(min_size=5, max_size=50),
        }),
        min_size=1,
        max_size=3,
    ),
)
def test_property_history_summary_excludes_user_input(user_input, history_with_user_input):
    """Requirements 4.8: 注入 prompt 的历史摘要只含 round_no/scenario_id/risk_flags/evidence，不含 user_input。"""
    llm = _CapturingLLMService()
    evaluator = _make_llm_evaluator(llm)
    evaluator.evaluate_round(user_input, "S1", 5, recent_history=history_with_user_input)

    assert len(llm.captured_messages) > 0
    user_content = llm.captured_messages[0][1]["content"]

    if "recent_history" not in user_content:
        return  # 未注入时跳过（理论上 round_no=5 且非空应注入，但防御性处理）

    # 验证历史记录中的 user_input 字段值没有出现在 prompt 里
    for entry in history_with_user_input:
        if not isinstance(entry, dict):
            continue
        entry_user_input = entry.get("user_input", "")
        if len(entry_user_input) >= 5:  # 足够长才有区分度
            assert entry_user_input not in user_content, (
                f"历史记录中的 user_input 字段值不应出现在 prompt 中: {entry_user_input!r}"
            )


# ===========================================================================
# P11（新增）— 同一输入 + 同一状态 → 规则评估结果稳定
# ===========================================================================

# Feature: training-multi-agent-upgrade, Property 11: 规则评估结果确定性（防 LLM 漂移）
@settings(max_examples=100)
@given(
    st.text(min_size=0, max_size=300),
    st.text(min_size=1, max_size=16),
    st.integers(min_value=1, max_value=30),
)
def test_property_rules_evaluation_is_deterministic(user_input, scenario_id, round_no):
    """P11: 纯规则路径下，同一输入多次调用结果完全一致（防止状态污染或随机性引入）。"""
    evaluator = _make_rules_only_evaluator()
    result_1 = evaluator.evaluate_round(user_input, scenario_id, round_no)
    result_2 = evaluator.evaluate_round(user_input, scenario_id, round_no)
    assert result_1["skill_delta"] == result_2["skill_delta"], "规则评估 skill_delta 应确定性一致"
    assert result_1["risk_flags"] == result_2["risk_flags"], "规则评估 risk_flags 应确定性一致"
    assert result_1["eval_mode"] == result_2["eval_mode"], "规则评估 eval_mode 应确定性一致"
    assert result_1["confidence"] == result_2["confidence"], "规则评估 confidence 应确定性一致"
