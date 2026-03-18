"""API数据模型（Pydantic Schemas）"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """通用API响应格式"""
    code: int = Field(default=200, description="状态码，200表示成功")
    message: str = Field(default="success", description="响应消息")
    data: Any = Field(default=None, description="响应数据")


class CreateCharacterRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., description="角色名称")
    appearance: Dict[str, Any] = Field(..., description="外观设定")
    personality: Dict[str, Any] = Field(..., description="性格设定")
    background: Dict[str, Any] = Field(..., description="背景设定")
    gender: Optional[str] = Field(None, description="性别（可选）")
    age: Optional[int] = Field(None, description="年龄（可选）")
    identity: Optional[str] = Field(None, description="身份（可选）")
    initial_scene: Optional[str] = Field(None, description="初始场景（可选）")
    initial_scene_prompt: Optional[str] = Field(None, description="初始场景提示（可选）")
    user_id: Optional[str] = Field(None, description="玩家ID（可选，用于图片文件命名）")
    image_type: Optional[str] = Field('portrait', description="图片类型（portrait=立绘, avatar=头像, scene=场景图，默认：portrait）")


class CharacterResponse(BaseModel):
    """角色信息响应"""
    character_id: str
    name: str
    appearance: Dict[str, Any]
    personality: Dict[str, Any]
    background: Dict[str, Any]
    gender: Optional[str] = None
    age: Optional[int] = None
    identity: Optional[str] = None
    initial_scene: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="角色图片URL列表（组图，供前端三选一）")


class GameInitRequest(BaseModel):
    """初始化游戏请求"""
    user_id: Optional[str] = Field(None, description="用户ID（可选，不提供则自动生成）")
    game_mode: str = Field(..., description="游戏模式：'solo' | 'story'")
    character_id: Optional[str] = Field(None, description="角色ID（可选）")


class GameInitResponse(BaseModel):
    """初始化游戏响应"""
    thread_id: str
    user_id: str
    game_mode: str


class GameInputRequest(BaseModel):
    """处理玩家输入请求"""
    thread_id: str = Field(..., description="线程ID")
    user_input: str = Field(..., description="玩家输入内容")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")
    character_id: Optional[str] = Field(None, description="角色ID（可选，用于会话恢复）")


class GameInputResponse(BaseModel):
    """处理玩家输入响应"""
    character_dialogue: Optional[str] = None
    player_options: Optional[List[Dict[str, Any]]] = None
    story_background: Optional[str] = None
    event_title: Optional[str] = None
    scene: Optional[str] = None
    is_event_finished: bool = False
    is_game_finished: bool = False


class CheckEndingResponse(BaseModel):
    """检查结局响应"""
    has_ending: bool = Field(..., description="是否满足结局条件")
    ending: Optional[Dict[str, Any]] = Field(None, description="结局信息（如果满足条件）")


class TriggerEndingRequest(BaseModel):
    """触发结局请求"""
    thread_id: str = Field(..., description="线程ID")


class InitializeStoryRequest(BaseModel):
    """初始化故事请求"""
    thread_id: str = Field(..., description="线程ID")
    character_id: str = Field(..., description="角色ID")
    scene_id: Optional[str] = Field('school', description="初遇大场景ID（可选，默认：school）")
    opening_event_id: Optional[str] = Field(None, description="初遇事件ID（可选，如果不提供则随机选择）")
    character_image_url: Optional[str] = Field(None, description="用户选择的角色图片URL（可选，如果不提供则使用最新图片）")


class CharacterImagesResponse(BaseModel):
    """角色图片响应"""
    images: List[str] = Field(default_factory=list, description="图片URL数组")


class RemoveBackgroundRequest(BaseModel):
    """去除背景请求"""
    image_url: Optional[str] = Field(None, description="图片URL（可选，如果不提供则使用角色最新图片）")
    image_urls: Optional[List[str]] = Field(None, description="所有图片URL列表（用于删除未选中的图片）")
    selected_index: Optional[int] = Field(None, description="选中的图片索引（0, 1, 2）")


class TrainingPlayerProfileRequest(BaseModel):
    """训练玩家档案请求。"""

    name: Optional[str] = Field(None, description="玩家姓名")
    gender: Optional[str] = Field(None, description="玩家性别")
    identity: Optional[str] = Field(None, description="玩家身份")
    age: Optional[int] = Field(None, description="玩家年龄")

    class Config:
        extra = "allow"


class TrainingInitRequest(BaseModel):
    """初始化训练请求"""
    user_id: str = Field(..., description="用户ID")
    character_id: Optional[int] = Field(None, description="角色ID（可选）")
    training_mode: str = Field(default="guided", description="训练模式：guided/self-paced/adaptive（兼容 self_paced 别名）")
    player_profile: Optional[TrainingPlayerProfileRequest] = Field(None, description="玩家身份档案（可选）")


class TrainingScenarioOptionResponse(BaseModel):
    """训练场景选项响应"""
    id: str
    label: str
    impact_hint: str = ""


class TrainingScenarioRecommendationResponse(BaseModel):
    """训练场景推荐元信息响应"""
    mode: str
    rank_score: float
    weakness_score: float
    state_boost_score: float
    risk_boost_score: float = 0.0
    phase_boost_score: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    rank: Optional[int] = None


class TrainingDecisionCandidateResponse(BaseModel):
    """训练决策上下文里的候选题摘要"""
    scenario_id: str
    title: str = ""
    rank: Optional[int] = None
    rank_score: float = 0.0
    is_selected: bool = False
    is_recommended: bool = False


class TrainingBranchTransitionResponse(BaseModel):
    """训练分支跳转响应。"""

    source_scenario_id: str
    target_scenario_id: str
    transition_type: str = "branch"
    reason: str = ""
    triggered_flags: List[str] = Field(default_factory=list)
    matched_rule: Dict[str, Any] = Field(default_factory=dict)


class TrainingBranchTransitionSummaryResponse(BaseModel):
    """训练分支跳转聚合摘要响应。"""

    source_scenario_id: str
    target_scenario_id: str
    transition_type: str = "branch"
    reason: str = ""
    count: int = 0
    round_nos: List[int] = Field(default_factory=list)
    triggered_flags: List[str] = Field(default_factory=list)


class TrainingRoundDecisionContextResponse(BaseModel):
    """训练回合提交时的推荐与选择上下文"""
    mode: str
    selection_source: str
    selected_scenario_id: str
    recommended_scenario_id: Optional[str] = None
    candidate_pool: List[TrainingDecisionCandidateResponse] = Field(default_factory=list)
    selected_recommendation: Optional[TrainingScenarioRecommendationResponse] = None
    recommended_recommendation: Optional[TrainingScenarioRecommendationResponse] = None
    selected_branch_transition: Optional[TrainingBranchTransitionResponse] = None
    recommended_branch_transition: Optional[TrainingBranchTransitionResponse] = None


class TrainingMetricObservationResponse(BaseModel):
    """训练观测中的单个能力或状态项"""
    code: str
    before: float = 0.0
    delta: float = 0.0
    after: float = 0.0
    is_target: bool = False


class TrainingKtObservationResponse(BaseModel):
    """训练回合的 KT 结构化观测响应"""
    scenario_id: str
    scenario_title: str = ""
    training_mode: str = "guided"
    round_no: Optional[int] = None
    primary_skill_code: Optional[str] = None
    primary_risk_flag: Optional[str] = None
    is_high_risk: bool = False
    target_skills: List[str] = Field(default_factory=list)
    weak_skills_before: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    focus_tags: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    skill_observations: List[TrainingMetricObservationResponse] = Field(default_factory=list)
    state_observations: List[TrainingMetricObservationResponse] = Field(default_factory=list)
    observation_summary: str = ""


class TrainingRecommendationLogResponse(BaseModel):
    """训练推荐日志响应"""
    round_no: int
    training_mode: str = "guided"
    selection_source: Optional[str] = None
    recommended_scenario_id: Optional[str] = None
    selected_scenario_id: Optional[str] = None
    candidate_pool: List[TrainingDecisionCandidateResponse] = Field(default_factory=list)
    recommended_recommendation: Optional[TrainingScenarioRecommendationResponse] = None
    selected_recommendation: Optional[TrainingScenarioRecommendationResponse] = None
    decision_context: Optional[TrainingRoundDecisionContextResponse] = None


class TrainingAuditEventResponse(BaseModel):
    """训练审计事件响应"""
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    round_no: Optional[int] = None
    timestamp: Optional[str] = None


class TrainingDiagnosticsCountItemResponse(BaseModel):
    """训练诊断摘要中的单个统计项响应"""
    code: str
    count: int = 0


class TrainingDiagnosticsSummaryResponse(BaseModel):
    """训练诊断摘要响应"""
    total_recommendation_logs: int = 0
    total_audit_events: int = 0
    total_kt_observations: int = 0
    high_risk_round_count: int = 0
    high_risk_round_nos: List[int] = Field(default_factory=list)
    recommended_vs_selected_mismatch_count: int = 0
    recommended_vs_selected_mismatch_rounds: List[int] = Field(default_factory=list)
    risk_flag_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    primary_skill_focus_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    top_weak_skills: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    selection_source_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    event_type_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    phase_tag_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    phase_transition_count: int = 0
    phase_transition_rounds: List[int] = Field(default_factory=list)
    panic_trigger_round_count: int = 0
    panic_trigger_rounds: List[int] = Field(default_factory=list)
    source_exposed_round_count: int = 0
    source_exposed_rounds: List[int] = Field(default_factory=list)
    editor_locked_round_count: int = 0
    editor_locked_rounds: List[int] = Field(default_factory=list)
    high_risk_path_round_count: int = 0
    high_risk_path_rounds: List[int] = Field(default_factory=list)
    branch_transition_count: int = 0
    branch_transition_rounds: List[int] = Field(default_factory=list)
    branch_transitions: List[TrainingBranchTransitionSummaryResponse] = Field(default_factory=list)
    last_primary_skill_code: Optional[str] = None
    last_primary_risk_flag: Optional[str] = None
    last_event_type: Optional[str] = None
    last_phase_tags: List[str] = Field(default_factory=list)
    last_branch_transition: Optional[TrainingBranchTransitionResponse] = None


class TrainingScenarioResponse(BaseModel):
    """训练场景响应"""
    id: str
    # 为兼容旧桩数据，标题允许缺省；正式服务输出仍会提供完整标题。
    title: str = ""
    era_date: str = ""
    location: str = ""
    brief: str = ""
    mission: str = ""
    decision_focus: str = ""
    target_skills: List[str] = Field(default_factory=list)
    risk_tags: List[str] = Field(default_factory=list)
    briefing: str = ""
    options: List[TrainingScenarioOptionResponse] = Field(default_factory=list)
    completion_hint: str = ""
    recommendation: Optional[TrainingScenarioRecommendationResponse] = None

    class Config:
        extra = "allow"


class TrainingEvaluationResponse(BaseModel):
    """训练评估响应"""
    llm_model: str = "rules_v1"
    confidence: float = 0.5
    risk_flags: List[str] = Field(default_factory=list)
    skill_delta: Dict[str, float] = Field(default_factory=dict)
    s_delta: Dict[str, float] = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)
    skill_scores_preview: Dict[str, float] = Field(default_factory=dict)
    eval_mode: str = "rules_only"
    fallback_reason: Optional[str] = None
    calibration: Optional[Dict[str, Any]] = None
    llm_raw_text: Optional[str] = None

    class Config:
        extra = "allow"


class TrainingPlayerProfileResponse(BaseModel):
    """训练玩家档案响应。"""

    name: Optional[str] = None
    gender: Optional[str] = None
    identity: Optional[str] = None
    age: Optional[int] = None

    class Config:
        extra = "allow"


class TrainingRuntimeFlagsResponse(BaseModel):
    """训练运行时 flags 响应。"""

    panic_triggered: bool = False
    source_exposed: bool = False
    editor_locked: bool = False
    high_risk_path: bool = False


class TrainingRuntimeStateBarResponse(BaseModel):
    """训练运行时状态条响应。"""

    editor_trust: float = 0.0
    public_stability: float = 0.0
    source_safety: float = 0.0


class TrainingConsequenceEventResponse(BaseModel):
    """训练运行时后果事件响应。"""

    event_type: str
    label: str = ""
    summary: str = ""
    severity: str = "medium"
    round_no: Optional[int] = None
    related_flag: Optional[str] = None
    state_bar: Optional[TrainingRuntimeStateBarResponse] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TrainingRuntimeStateResponse(BaseModel):
    """训练统一运行时状态响应。"""

    current_round_no: int
    current_scene_id: Optional[str] = None
    k_state: Dict[str, float] = Field(default_factory=dict)
    s_state: Dict[str, float] = Field(default_factory=dict)
    runtime_flags: TrainingRuntimeFlagsResponse = Field(default_factory=TrainingRuntimeFlagsResponse)
    state_bar: TrainingRuntimeStateBarResponse = Field(default_factory=TrainingRuntimeStateBarResponse)
    player_profile: Optional[TrainingPlayerProfileResponse] = None


class TrainingInitResponse(BaseModel):
    """初始化训练响应"""
    session_id: str
    status: str
    round_no: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    next_scenario: Optional[TrainingScenarioResponse] = None
    scenario_candidates: Optional[List[TrainingScenarioResponse]] = None


class TrainingScenarioNextRequest(BaseModel):
    """获取下一场景请求"""
    session_id: str = Field(..., description="训练会话ID")


class TrainingScenarioNextResponse(BaseModel):
    """获取下一场景响应"""
    session_id: str
    status: str
    round_no: int
    scenario: Optional[TrainingScenarioResponse] = None
    scenario_candidates: Optional[List[TrainingScenarioResponse]] = None
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    ending: Optional[Dict[str, Any]] = None


class TrainingRoundSubmitRequest(BaseModel):
    """提交训练回合请求"""
    session_id: str = Field(..., description="训练会话ID")
    scenario_id: str = Field(..., description="场景ID")
    user_input: str = Field(..., description="用户输入")
    selected_option: Optional[str] = Field(None, description="所选选项编码（可选）")


class TrainingRoundSubmitResponse(BaseModel):
    """提交训练回合响应"""
    session_id: str
    round_no: int
    evaluation: TrainingEvaluationResponse
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    consequence_events: List[TrainingConsequenceEventResponse] = Field(default_factory=list)
    is_completed: bool
    ending: Optional[Dict[str, Any]] = None
    decision_context: Optional[TrainingRoundDecisionContextResponse] = None


class TrainingProgressResponse(BaseModel):
    """训练进度响应"""
    session_id: str
    status: str
    round_no: int
    total_rounds: int
    k_state: Dict[str, float]
    s_state: Dict[str, float]
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None


class TrainingReportHistoryItemResponse(BaseModel):
    """训练报告中的单回合历史项"""
    round_no: int
    scenario_id: str
    user_input: str
    selected_option: Optional[str] = None
    evaluation: Optional[TrainingEvaluationResponse] = None
    k_state_before: Dict[str, float]
    k_state_after: Dict[str, float]
    s_state_before: Dict[str, float]
    s_state_after: Dict[str, float]
    timestamp: Optional[str] = None
    decision_context: Optional[TrainingRoundDecisionContextResponse] = None
    kt_observation: Optional[TrainingKtObservationResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    consequence_events: List[TrainingConsequenceEventResponse] = Field(default_factory=list)


class TrainingReportMetricResponse(BaseModel):
    """训练报告中的单个能力或状态指标摘要"""
    code: str
    initial: float = 0.0
    final: float = 0.0
    delta: float = 0.0
    weight: Optional[float] = None
    is_lowest_final: bool = False
    is_highest_gain: bool = False


class TrainingReportCurvePointResponse(BaseModel):
    """训练报告中的成长曲线点"""
    round_no: int
    scenario_id: Optional[str] = None
    scenario_title: str = ""
    k_state: Dict[str, float] = Field(default_factory=dict)
    s_state: Dict[str, float] = Field(default_factory=dict)
    weighted_k_score: float = 0.0
    is_high_risk: bool = False
    risk_flags: List[str] = Field(default_factory=list)
    primary_skill_code: Optional[str] = None
    timestamp: Optional[str] = None


class TrainingReportSummaryResponse(BaseModel):
    """训练报告摘要响应"""
    weighted_score_initial: float = 0.0
    weighted_score_final: float = 0.0
    weighted_score_delta: float = 0.0
    strongest_improved_skill_code: Optional[str] = None
    strongest_improved_skill_delta: float = 0.0
    weakest_skill_code: Optional[str] = None
    weakest_skill_score: float = 0.0
    dominant_risk_flag: Optional[str] = None
    high_risk_round_count: int = 0
    high_risk_round_nos: List[int] = Field(default_factory=list)
    panic_trigger_round_count: int = 0
    source_exposed_round_count: int = 0
    editor_locked_round_count: int = 0
    high_risk_path_round_count: int = 0
    branch_transition_count: int = 0
    branch_transition_rounds: List[int] = Field(default_factory=list)
    branch_transitions: List[TrainingBranchTransitionSummaryResponse] = Field(default_factory=list)
    risk_flag_counts: List[TrainingDiagnosticsCountItemResponse] = Field(default_factory=list)
    completed_scenario_ids: List[str] = Field(default_factory=list)
    review_suggestions: List[str] = Field(default_factory=list)


class TrainingReportResponse(BaseModel):
    """训练报告响应"""
    session_id: str
    status: str
    rounds: int
    k_state_final: Dict[str, float]
    s_state_final: Dict[str, float]
    improvement: float
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    ending: Optional[Dict[str, Any]] = None
    summary: Optional[TrainingReportSummaryResponse] = None
    ability_radar: List[TrainingReportMetricResponse] = Field(default_factory=list)
    state_radar: List[TrainingReportMetricResponse] = Field(default_factory=list)
    growth_curve: List[TrainingReportCurvePointResponse] = Field(default_factory=list)
    history: List[TrainingReportHistoryItemResponse] = Field(default_factory=list)


class TrainingDiagnosticsResponse(BaseModel):
    """训练诊断响应"""
    session_id: str
    status: str
    round_no: int
    player_profile: Optional[TrainingPlayerProfileResponse] = None
    runtime_state: Optional[TrainingRuntimeStateResponse] = None
    summary: Optional[TrainingDiagnosticsSummaryResponse] = None
    recommendation_logs: List[TrainingRecommendationLogResponse] = Field(default_factory=list)
    audit_events: List[TrainingAuditEventResponse] = Field(default_factory=list)
    kt_observations: List[TrainingKtObservationResponse] = Field(default_factory=list)


class TrainingInitApiResponse(ApiResponse):
    """训练初始化接口响应包装"""
    data: Optional[TrainingInitResponse] = None


class TrainingScenarioNextApiResponse(ApiResponse):
    """下一场景接口响应包装"""
    data: Optional[TrainingScenarioNextResponse] = None


class TrainingRoundSubmitApiResponse(ApiResponse):
    """提交回合接口响应包装"""
    data: Optional[TrainingRoundSubmitResponse] = None


class TrainingProgressApiResponse(ApiResponse):
    """训练进度接口响应包装"""
    data: Optional[TrainingProgressResponse] = None


class TrainingReportApiResponse(ApiResponse):
    """训练报告接口响应包装"""
    data: Optional[TrainingReportResponse] = None


class TrainingDiagnosticsApiResponse(ApiResponse):
    """训练诊断接口响应包装"""
    data: Optional[TrainingDiagnosticsResponse] = None
