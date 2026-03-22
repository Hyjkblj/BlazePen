import type { PlayerOption } from '@/types/game';

export type GenericApiRecord = Record<string, unknown>;

export interface ApiStructuredError extends GenericApiRecord {
  code?: string;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface ApiResponse<T = unknown> extends GenericApiRecord {
  code?: number;
  message?: string;
  data?: T;
  error?: unknown;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface ApiErrorData extends GenericApiRecord {
  code?: number;
  message?: string;
  detail?: unknown;
  error?: ApiStructuredError | unknown;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface CreateCharacterRequest {
  name: string;
  appearance: Record<string, unknown>;
  personality: Record<string, unknown>;
  background: Record<string, unknown>;
  gender?: string;
  age?: number;
  identity?: string;
  initial_scene?: string;
  initial_scene_prompt?: string;
}

export interface CreateCharacterResponse extends GenericApiRecord {
  character_id?: string | number;
  name?: string;
  image_url?: string;
  image_urls?: string[];
}

export interface CharacterImagesResponse {
  images?: string[];
}

export interface StoryResponsePayload extends GenericApiRecord {
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  is_game_finished?: boolean;
  snapshot?: GenericApiRecord | null;
}

export interface LegacyStoryEndingPayload extends GenericApiRecord {
  type?: string;
  description?: string;
  favorability?: number | string | null;
  trust?: number | string | null;
  hostility?: number | string | null;
}

export interface StoryEndingKeyStatesPayload extends GenericApiRecord {
  favorability?: number | string | null;
  trust?: number | string | null;
  hostility?: number | string | null;
  dependence?: number | string | null;
}

export interface StoryEndingSummaryItemPayload extends GenericApiRecord {
  type?: string;
  description?: string;
  scene?: string | null;
  event_title?: string | null;
  key_states?: StoryEndingKeyStatesPayload | null;
}

export interface RemoveBackgroundResponse {
  original_url: string;
  transparent_url: string;
  local_path: string;
  selected_image_url?: string;
}

export interface InitializeStoryResponse extends StoryResponsePayload {
  thread_id?: string;
}

export interface SceneApiItem extends GenericApiRecord {
  id?: string;
  name?: string;
  description?: string;
  imageUrl?: string;
}

export interface GetScenesResponse extends GenericApiRecord {
  scenes?: SceneApiItem[];
}

export interface GameInitRequest {
  user_id?: string;
  game_mode: string;
  character_id: string;
}

export interface GameInputRequest {
  thread_id: string;
  user_input: string;
  user_id?: string;
  character_id?: string;
}

export interface GameInitResponse extends GenericApiRecord {
  thread_id?: string;
  user_id?: string;
  game_mode?: string;
}

export interface ProcessGameInputResponse extends StoryResponsePayload {
  thread_id?: string;
  round_no?: number;
  status?: string;
  session_restored?: boolean;
  need_reselect_option?: boolean;
  restored_from_thread_id?: string;
}

export interface StorySessionSnapshotResponse extends ProcessGameInputResponse {
  updated_at?: string;
  expires_at?: string;
}

export interface CheckEndingResponse extends GenericApiRecord {
  has_ending?: boolean;
  ending?: LegacyStoryEndingPayload | null;
}

export interface StoryEndingSummaryResponse extends GenericApiRecord {
  thread_id?: string;
  status?: string;
  round_no?: number;
  has_ending?: boolean;
  ending?: StoryEndingSummaryItemPayload | null;
  updated_at?: string;
  expires_at?: string;
}

export interface StoryHistoryUserActionPayload extends GenericApiRecord {
  kind?: string;
  summary?: string;
  raw_input?: string | null;
  option_index?: number | null;
  option_text?: string | null;
  option_type?: string | null;
}

export interface StoryHistoryStateSummaryPayload extends GenericApiRecord {
  changes?: Record<string, unknown> | null;
  current_states?: Record<string, unknown> | null;
}

export interface StoryHistoryItemPayload extends GenericApiRecord {
  round_no?: number;
  status?: string;
  scene?: string | null;
  event_title?: string | null;
  character_dialogue?: string | null;
  user_action?: StoryHistoryUserActionPayload | null;
  state_summary?: StoryHistoryStateSummaryPayload | null;
  is_event_finished?: boolean;
  is_game_finished?: boolean;
  created_at?: string | null;
}

export interface StorySessionHistoryResponse extends GenericApiRecord {
  thread_id?: string;
  status?: string;
  current_round_no?: number;
  latest_scene?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  history?: StoryHistoryItemPayload[] | null;
  latest_snapshot?: GenericApiRecord | null;
}

export interface PresetVoiceItem {
  id: string;
  name: string;
  description?: string;
  voice_id?: string | null;
  gender?: string;
  style?: string;
  preview_text?: string;
}

export interface PresetVoiceGroups {
  female?: PresetVoiceItem[];
  male?: PresetVoiceItem[];
  neutral?: PresetVoiceItem[];
  [key: string]: PresetVoiceItem[] | undefined;
}

export interface PresetVoicesResponse {
  voices?: PresetVoiceItem[] | PresetVoiceGroups;
}

export interface GenerateSpeechOptions {
  use_cache?: boolean;
  emotion_params?: Record<string, unknown>;
}

export interface GenerateSpeechResponse {
  audio_url: string;
  duration?: number;
  cached?: boolean;
}

export interface VoicePreviewResponse {
  audio_url: string;
  duration?: number;
}

export interface SetVoiceConfigRequest {
  character_id: number;
  voice_type: string;
  preset_voice_id?: string | null;
  voice_design_description?: string | null;
  voice_params?: Record<string, unknown>;
}

export interface TrainingPlayerProfileApi {
  name?: string | null;
  gender?: string | null;
  identity?: string | null;
  age?: number | string | null;
}

export interface TrainingScenarioOptionApiResponse extends GenericApiRecord {
  id?: string;
  label?: string;
  impact_hint?: string | null;
}

export interface TrainingScenarioRecommendationApiResponse extends GenericApiRecord {
  mode?: string;
  rank_score?: number | string | null;
  weakness_score?: number | string | null;
  state_boost_score?: number | string | null;
  risk_boost_score?: number | string | null;
  phase_boost_score?: number | string | null;
  reasons?: string[] | null;
  rank?: number | string | null;
}

export interface TrainingDecisionCandidateApiResponse extends GenericApiRecord {
  scenario_id?: string;
  title?: string | null;
  rank?: number | string | null;
  rank_score?: number | string | null;
  is_selected?: boolean;
  is_recommended?: boolean;
}

export interface TrainingBranchTransitionApiResponse extends GenericApiRecord {
  source_scenario_id?: string;
  target_scenario_id?: string;
  transition_type?: string | null;
  reason?: string | null;
  triggered_flags?: string[] | null;
  matched_rule?: Record<string, unknown> | null;
}

export interface TrainingRoundDecisionContextApiResponse extends GenericApiRecord {
  mode?: string;
  selection_source?: string | null;
  selected_scenario_id?: string;
  recommended_scenario_id?: string | null;
  candidate_pool?: TrainingDecisionCandidateApiResponse[] | null;
  selected_recommendation?: TrainingScenarioRecommendationApiResponse | null;
  recommended_recommendation?: TrainingScenarioRecommendationApiResponse | null;
  selected_branch_transition?: TrainingBranchTransitionApiResponse | null;
  recommended_branch_transition?: TrainingBranchTransitionApiResponse | null;
}

export interface TrainingScenarioApiResponse extends GenericApiRecord {
  id?: string;
  title?: string | null;
  era_date?: string | null;
  location?: string | null;
  brief?: string | null;
  mission?: string | null;
  decision_focus?: string | null;
  target_skills?: string[] | null;
  risk_tags?: string[] | null;
  options?: TrainingScenarioOptionApiResponse[] | null;
  completion_hint?: string | null;
  recommendation?: TrainingScenarioRecommendationApiResponse | null;
}

export interface TrainingEvaluationApiResponse extends GenericApiRecord {
  llm_model?: string | null;
  confidence?: number | string | null;
  risk_flags?: string[] | null;
  skill_delta?: Record<string, unknown> | null;
  s_delta?: Record<string, unknown> | null;
  evidence?: string[] | null;
  skill_scores_preview?: Record<string, unknown> | null;
  eval_mode?: string | null;
  fallback_reason?: string | null;
  calibration?: Record<string, unknown> | null;
  llm_raw_text?: string | null;
}

export interface TrainingRuntimeFlagsApiResponse extends GenericApiRecord {
  panic_triggered?: boolean;
  source_exposed?: boolean;
  editor_locked?: boolean;
  high_risk_path?: boolean;
}

export interface TrainingRuntimeStateBarApiResponse extends GenericApiRecord {
  editor_trust?: number | string | null;
  public_stability?: number | string | null;
  source_safety?: number | string | null;
}

export interface TrainingConsequenceEventApiResponse extends GenericApiRecord {
  event_type?: string;
  label?: string | null;
  summary?: string | null;
  severity?: string | null;
  round_no?: number | string | null;
  related_flag?: string | null;
  state_bar?: TrainingRuntimeStateBarApiResponse | null;
  payload?: Record<string, unknown> | null;
}

export interface TrainingRuntimeStateApiResponse extends GenericApiRecord {
  current_round_no?: number | string | null;
  current_scene_id?: string | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  runtime_flags?: TrainingRuntimeFlagsApiResponse | null;
  state_bar?: TrainingRuntimeStateBarApiResponse | null;
  player_profile?: TrainingPlayerProfileApi | null;
}

export interface TrainingInitRequest extends GenericApiRecord {
  user_id: string;
  character_id?: number;
  training_mode?: string;
  player_profile?: TrainingPlayerProfileApi | null;
}

export interface TrainingInitResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  round_no?: number | string | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  next_scenario?: TrainingScenarioApiResponse | null;
  scenario_candidates?: TrainingScenarioApiResponse[] | null;
}

export interface TrainingScenarioNextRequest extends GenericApiRecord {
  session_id: string;
}

export interface TrainingScenarioNextResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  round_no?: number | string | null;
  scenario?: TrainingScenarioApiResponse | null;
  scenario_candidates?: TrainingScenarioApiResponse[] | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  ending?: Record<string, unknown> | null;
}

export interface TrainingRoundSubmitRequest extends GenericApiRecord {
  session_id: string;
  scenario_id: string;
  user_input: string;
  selected_option?: string | null;
}

export interface TrainingRoundSubmitResponse extends GenericApiRecord {
  session_id?: string;
  round_no?: number | string | null;
  evaluation?: TrainingEvaluationApiResponse | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  consequence_events?: TrainingConsequenceEventApiResponse[] | null;
  is_completed?: boolean;
  ending?: Record<string, unknown> | null;
  decision_context?: TrainingRoundDecisionContextApiResponse | null;
}

export interface TrainingProgressResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  round_no?: number | string | null;
  total_rounds?: number | string | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
}

export interface TrainingSessionProgressAnchorResponse extends GenericApiRecord {
  current_round_no?: number | string | null;
  total_rounds?: number | string | null;
  completed_rounds?: number | string | null;
  remaining_rounds?: number | string | null;
  progress_percent?: number | string | null;
  next_round_no?: number | string | null;
}

export interface TrainingSessionSummaryResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  training_mode?: string | null;
  current_round_no?: number | string | null;
  total_rounds?: number | string | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  progress_anchor?: TrainingSessionProgressAnchorResponse | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  resumable_scenario?: TrainingScenarioApiResponse | null;
  scenario_candidates?: TrainingScenarioApiResponse[] | null;
  can_resume?: boolean;
  is_completed?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  end_time?: string | null;
}

export interface TrainingReportHistoryItemApiResponse extends GenericApiRecord {
  round_no?: number | string | null;
  scenario_id?: string | null;
  user_input?: string | null;
  selected_option?: string | null;
  evaluation?: TrainingEvaluationApiResponse | null;
  k_state_before?: Record<string, unknown> | null;
  k_state_after?: Record<string, unknown> | null;
  s_state_before?: Record<string, unknown> | null;
  s_state_after?: Record<string, unknown> | null;
  timestamp?: string | null;
  decision_context?: TrainingRoundDecisionContextApiResponse | null;
  kt_observation?: TrainingKtObservationApiResponse | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  consequence_events?: TrainingConsequenceEventApiResponse[] | null;
}

export interface TrainingHistoryResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  training_mode?: string | null;
  current_round_no?: number | string | null;
  total_rounds?: number | string | null;
  progress_anchor?: TrainingSessionProgressAnchorResponse | null;
  history?: TrainingReportHistoryItemApiResponse[] | null;
  is_completed?: boolean;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  created_at?: string | null;
  updated_at?: string | null;
  end_time?: string | null;
}

export interface TrainingReportMetricApiResponse extends GenericApiRecord {
  code?: string;
  initial?: number | string | null;
  final?: number | string | null;
  delta?: number | string | null;
  weight?: number | string | null;
  is_lowest_final?: boolean;
  is_highest_gain?: boolean;
}

export interface TrainingReportCurvePointApiResponse extends GenericApiRecord {
  round_no?: number | string | null;
  scenario_id?: string | null;
  scenario_title?: string | null;
  k_state?: Record<string, unknown> | null;
  s_state?: Record<string, unknown> | null;
  weighted_k_score?: number | string | null;
  is_high_risk?: boolean;
  risk_flags?: string[] | null;
  primary_skill_code?: string | null;
  timestamp?: string | null;
}

export interface TrainingMetricObservationApiResponse extends GenericApiRecord {
  code?: string;
  before?: number | string | null;
  delta?: number | string | null;
  after?: number | string | null;
  is_target?: boolean;
}

export interface TrainingKtObservationApiResponse extends GenericApiRecord {
  scenario_id?: string;
  scenario_title?: string | null;
  training_mode?: string | null;
  round_no?: number | string | null;
  primary_skill_code?: string | null;
  primary_risk_flag?: string | null;
  is_high_risk?: boolean;
  target_skills?: string[] | null;
  weak_skills_before?: string[] | null;
  risk_flags?: string[] | null;
  focus_tags?: string[] | null;
  evidence?: string[] | null;
  skill_observations?: TrainingMetricObservationApiResponse[] | null;
  state_observations?: TrainingMetricObservationApiResponse[] | null;
  observation_summary?: string | null;
}

export interface TrainingRecommendationLogApiResponse extends GenericApiRecord {
  round_no?: number | string | null;
  training_mode?: string | null;
  selection_source?: string | null;
  recommended_scenario_id?: string | null;
  selected_scenario_id?: string | null;
  candidate_pool?: TrainingDecisionCandidateApiResponse[] | null;
  recommended_recommendation?: TrainingScenarioRecommendationApiResponse | null;
  selected_recommendation?: TrainingScenarioRecommendationApiResponse | null;
  decision_context?: TrainingRoundDecisionContextApiResponse | null;
}

export interface TrainingAuditEventApiResponse extends GenericApiRecord {
  event_type?: string;
  payload?: Record<string, unknown> | null;
  round_no?: number | string | null;
  timestamp?: string | null;
}

export interface TrainingDiagnosticsCountItemApiResponse extends GenericApiRecord {
  code?: string;
  count?: number | string | null;
}

export interface TrainingBranchTransitionSummaryApiResponse extends GenericApiRecord {
  source_scenario_id?: string;
  target_scenario_id?: string;
  transition_type?: string | null;
  reason?: string | null;
  count?: number | string | null;
  round_nos?: Array<number | string> | null;
  triggered_flags?: string[] | null;
}

export interface TrainingDiagnosticsSummaryApiResponse extends GenericApiRecord {
  total_recommendation_logs?: number | string | null;
  total_audit_events?: number | string | null;
  total_kt_observations?: number | string | null;
  high_risk_round_count?: number | string | null;
  high_risk_round_nos?: Array<number | string> | null;
  recommended_vs_selected_mismatch_count?: number | string | null;
  recommended_vs_selected_mismatch_rounds?: Array<number | string> | null;
  risk_flag_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  primary_skill_focus_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  top_weak_skills?: TrainingDiagnosticsCountItemApiResponse[] | null;
  selection_source_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  event_type_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  phase_tag_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  phase_transition_count?: number | string | null;
  phase_transition_rounds?: Array<number | string> | null;
  panic_trigger_round_count?: number | string | null;
  panic_trigger_rounds?: Array<number | string> | null;
  source_exposed_round_count?: number | string | null;
  source_exposed_rounds?: Array<number | string> | null;
  editor_locked_round_count?: number | string | null;
  editor_locked_rounds?: Array<number | string> | null;
  high_risk_path_round_count?: number | string | null;
  high_risk_path_rounds?: Array<number | string> | null;
  branch_transition_count?: number | string | null;
  branch_transition_rounds?: Array<number | string> | null;
  branch_transitions?: TrainingBranchTransitionSummaryApiResponse[] | null;
  last_primary_skill_code?: string | null;
  last_primary_risk_flag?: string | null;
  last_event_type?: string | null;
  last_phase_tags?: string[] | null;
  last_branch_transition?: TrainingBranchTransitionApiResponse | null;
}

export interface TrainingReportSummaryApiResponse extends GenericApiRecord {
  weighted_score_initial?: number | string | null;
  weighted_score_final?: number | string | null;
  weighted_score_delta?: number | string | null;
  strongest_improved_skill_code?: string | null;
  strongest_improved_skill_delta?: number | string | null;
  weakest_skill_code?: string | null;
  weakest_skill_score?: number | string | null;
  dominant_risk_flag?: string | null;
  high_risk_round_count?: number | string | null;
  high_risk_round_nos?: Array<number | string> | null;
  panic_trigger_round_count?: number | string | null;
  source_exposed_round_count?: number | string | null;
  editor_locked_round_count?: number | string | null;
  high_risk_path_round_count?: number | string | null;
  branch_transition_count?: number | string | null;
  branch_transition_rounds?: Array<number | string> | null;
  branch_transitions?: TrainingBranchTransitionSummaryApiResponse[] | null;
  risk_flag_counts?: TrainingDiagnosticsCountItemApiResponse[] | null;
  completed_scenario_ids?: string[] | null;
  review_suggestions?: string[] | null;
}

export interface TrainingReportResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  rounds?: number | string | null;
  k_state_final?: Record<string, unknown> | null;
  s_state_final?: Record<string, unknown> | null;
  improvement?: number | string | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  ending?: Record<string, unknown> | null;
  summary?: TrainingReportSummaryApiResponse | null;
  ability_radar?: TrainingReportMetricApiResponse[] | null;
  state_radar?: TrainingReportMetricApiResponse[] | null;
  growth_curve?: TrainingReportCurvePointApiResponse[] | null;
  history?: TrainingReportHistoryItemApiResponse[] | null;
}

export interface TrainingDiagnosticsResponse extends GenericApiRecord {
  session_id?: string;
  status?: string | null;
  round_no?: number | string | null;
  player_profile?: TrainingPlayerProfileApi | null;
  runtime_state?: TrainingRuntimeStateApiResponse | null;
  summary?: TrainingDiagnosticsSummaryApiResponse | null;
  recommendation_logs?: TrainingRecommendationLogApiResponse[] | null;
  audit_events?: TrainingAuditEventApiResponse[] | null;
  kt_observations?: TrainingKtObservationApiResponse[] | null;
}
