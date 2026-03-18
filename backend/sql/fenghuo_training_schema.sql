-- Fenghuo Bifeng training schema (PostgreSQL)
-- Date: 2026-03-13
-- Notes:
-- 1) This schema is additive and can coexist with existing gameplay tables.
-- 2) It is designed for: history constraints + structured scoring + KT + adaptive recommendation.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) History anchors (immutable facts)
CREATE TABLE IF NOT EXISTS history_timeline_events (
    id BIGSERIAL PRIMARY KEY,
    event_code VARCHAR(64) NOT NULL UNIQUE,
    event_date DATE NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    event_summary TEXT NOT NULL,
    is_hard_anchor BOOLEAN NOT NULL DEFAULT TRUE,
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_history_timeline_events_date
ON history_timeline_events (event_date);

-- 2) Scenario bank
CREATE TABLE IF NOT EXISTS scenario_bank (
    scenario_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    anchor_event_code VARCHAR(64) REFERENCES history_timeline_events(event_code),
    era_date DATE NOT NULL,
    risk_level SMALLINT NOT NULL CHECK (risk_level BETWEEN 1 AND 5),
    target_skills TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    objective TEXT NOT NULL,
    setup_prompt TEXT NOT NULL,
    max_rounds INTEGER NOT NULL DEFAULT 3 CHECK (max_rounds > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenario_bank_active_risk
ON scenario_bank (is_active, risk_level);

-- 3) Decision nodes in each scenario
CREATE TABLE IF NOT EXISTS scenario_decision_nodes (
    id BIGSERIAL PRIMARY KEY,
    scenario_id VARCHAR(64) NOT NULL REFERENCES scenario_bank(scenario_id) ON DELETE CASCADE,
    node_code VARCHAR(64) NOT NULL,
    round_no INTEGER NOT NULL CHECK (round_no > 0),
    node_type VARCHAR(32) NOT NULL CHECK (node_type IN ('single_choice', 'multi_choice', 'free_text')),
    question_text TEXT NOT NULL,
    rubric_focus TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scenario_id, node_code)
);

CREATE INDEX IF NOT EXISTS idx_scenario_decision_nodes_scenario_round
ON scenario_decision_nodes (scenario_id, round_no);

-- 4) Options for each decision node
CREATE TABLE IF NOT EXISTS scenario_options (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL REFERENCES scenario_decision_nodes(id) ON DELETE CASCADE,
    option_code VARCHAR(64) NOT NULL,
    option_text TEXT NOT NULL,
    effect_s_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    effect_k_hint JSONB NOT NULL DEFAULT '{}'::jsonb,
    ethics_risk SMALLINT NOT NULL DEFAULT 0 CHECK (ethics_risk BETWEEN 0 AND 5),
    evidence_requirement SMALLINT NOT NULL DEFAULT 0 CHECK (evidence_requirement BETWEEN 0 AND 5),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (node_id, option_code)
);

CREATE INDEX IF NOT EXISTS idx_scenario_options_node_id
ON scenario_options (node_id);

-- 5) Training session
CREATE TABLE IF NOT EXISTS training_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(128) NOT NULL,
    character_id INTEGER NULL REFERENCES characters(id),
    training_mode VARCHAR(32) NOT NULL DEFAULT 'guided',
    status VARCHAR(32) NOT NULL DEFAULT 'initialized'
        CHECK (status IN ('initialized', 'in_progress', 'completed', 'aborted')),
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ NULL,
    current_scenario_id VARCHAR(64) NULL REFERENCES scenario_bank(scenario_id),
    current_round_no INTEGER NOT NULL DEFAULT 0 CHECK (current_round_no >= 0),
    k_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    s_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    pretest JSONB NOT NULL DEFAULT '{}'::jsonb,
    posttest JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_sessions_user_status
ON training_sessions (user_id, status);

-- 6) Round submissions
CREATE TABLE IF NOT EXISTS training_rounds (
    round_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL CHECK (round_no > 0),
    scenario_id VARCHAR(64) NOT NULL REFERENCES scenario_bank(scenario_id),
    node_id BIGINT NULL REFERENCES scenario_decision_nodes(id),
    node_code VARCHAR(64) NULL,
    user_input_raw TEXT NOT NULL,
    selected_option VARCHAR(64) NULL,
    user_action JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_before JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_after JSONB NOT NULL DEFAULT '{}'::jsonb,
    kt_before JSONB NOT NULL DEFAULT '{}'::jsonb,
    kt_after JSONB NOT NULL DEFAULT '{}'::jsonb,
    feedback_text TEXT NULL,
    submit_latency_ms INTEGER NULL CHECK (submit_latency_ms IS NULL OR submit_latency_ms >= 0),
    submit_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, round_no)
);

CREATE INDEX IF NOT EXISTS idx_training_rounds_session_round
ON training_rounds (session_id, round_no);

CREATE INDEX IF NOT EXISTS idx_training_rounds_scenario
ON training_rounds (scenario_id);

-- 7) Evaluation details
CREATE TABLE IF NOT EXISTS round_evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL UNIQUE REFERENCES training_rounds(round_id) ON DELETE CASCADE,
    llm_model VARCHAR(128) NOT NULL,
    confidence NUMERIC(6,5) NOT NULL DEFAULT 0.5 CHECK (confidence BETWEEN 0 AND 1),
    risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    s_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    skill_scores_preview JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_round_evaluations_raw_payload_gin
ON round_evaluations USING GIN (raw_payload);

CREATE INDEX IF NOT EXISTS idx_round_evaluations_evidence_gin
ON round_evaluations USING GIN (evidence);

-- 8) KT observation (per skill, per round)
CREATE TABLE IF NOT EXISTS kt_observations (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES training_rounds(round_id) ON DELETE CASCADE,
    skill_code VARCHAR(8) NOT NULL CHECK (skill_code IN ('K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7', 'K8')),
    observed_score NUMERIC(6,5) NOT NULL CHECK (observed_score BETWEEN 0 AND 1),
    confidence NUMERIC(6,5) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source VARCHAR(32) NOT NULL CHECK (source IN ('llm', 'rule', 'hybrid')),
    evidence TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kt_observations_session_skill_time
ON kt_observations (session_id, skill_code, created_at);

-- 9) KT snapshots
CREATE TABLE IF NOT EXISTS kt_state_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL CHECK (round_no >= 0),
    k1 NUMERIC(6,5) NOT NULL CHECK (k1 BETWEEN 0 AND 1),
    k2 NUMERIC(6,5) NOT NULL CHECK (k2 BETWEEN 0 AND 1),
    k3 NUMERIC(6,5) NOT NULL CHECK (k3 BETWEEN 0 AND 1),
    k4 NUMERIC(6,5) NOT NULL CHECK (k4 BETWEEN 0 AND 1),
    k5 NUMERIC(6,5) NOT NULL CHECK (k5 BETWEEN 0 AND 1),
    k6 NUMERIC(6,5) NOT NULL CHECK (k6 BETWEEN 0 AND 1),
    k7 NUMERIC(6,5) NOT NULL CHECK (k7 BETWEEN 0 AND 1),
    k8 NUMERIC(6,5) NOT NULL CHECK (k8 BETWEEN 0 AND 1),
    uncertainty JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendation_hint JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, round_no)
);

CREATE INDEX IF NOT EXISTS idx_kt_state_snapshots_session_round
ON kt_state_snapshots (session_id, round_no DESC);

-- 10) Narrative state snapshots (plot state vector S)
CREATE TABLE IF NOT EXISTS narrative_state_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL CHECK (round_no >= 0),
    credibility NUMERIC(6,5) NOT NULL CHECK (credibility BETWEEN 0 AND 1),
    accuracy NUMERIC(6,5) NOT NULL CHECK (accuracy BETWEEN 0 AND 1),
    public_panic NUMERIC(6,5) NOT NULL CHECK (public_panic BETWEEN 0 AND 1),
    source_safety NUMERIC(6,5) NOT NULL CHECK (source_safety BETWEEN 0 AND 1),
    editor_trust NUMERIC(6,5) NOT NULL CHECK (editor_trust BETWEEN 0 AND 1),
    actionability NUMERIC(6,5) NOT NULL CHECK (actionability BETWEEN 0 AND 1),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, round_no)
);

CREATE INDEX IF NOT EXISTS idx_narrative_state_snapshots_session_round
ON narrative_state_snapshots (session_id, round_no DESC);

-- 11) Recommendation logs
CREATE TABLE IF NOT EXISTS scenario_recommendation_logs (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    from_round_no INTEGER NOT NULL CHECK (from_round_no >= 0),
    selected_scenario_id VARCHAR(64) NOT NULL REFERENCES scenario_bank(scenario_id),
    candidate_scores JSONB NOT NULL DEFAULT '[]'::jsonb,
    utility_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version VARCHAR(64) NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenario_recommendation_logs_session_round
ON scenario_recommendation_logs (session_id, from_round_no DESC);

-- 12) Ending and report
CREATE TABLE IF NOT EXISTS ending_results (
    ending_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    ending_type VARCHAR(64) NOT NULL,
    ending_score NUMERIC(6,5) NOT NULL CHECK (ending_score BETWEEN 0 AND 1),
    severe_violation_count INTEGER NOT NULL DEFAULT 0 CHECK (severe_violation_count >= 0),
    explanation TEXT NOT NULL,
    evidence_round_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    report_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13) Auditing
CREATE TABLE IF NOT EXISTS training_audit_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_id UUID NULL REFERENCES training_rounds(round_id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    event_level VARCHAR(16) NOT NULL DEFAULT 'info' CHECK (event_level IN ('debug', 'info', 'warn', 'error')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_audit_events_session_time
ON training_audit_events (session_id, created_at DESC);

-- 14) SQL <-> vector db mapping
CREATE TABLE IF NOT EXISTS memory_index_refs (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES training_sessions(session_id) ON DELETE CASCADE,
    round_id UUID NULL REFERENCES training_rounds(round_id) ON DELETE CASCADE,
    chroma_collection VARCHAR(128) NOT NULL,
    chroma_doc_id VARCHAR(256) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chroma_collection, chroma_doc_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_index_refs_session
ON memory_index_refs (session_id, created_at DESC);

-- 15) Convenience view: latest progress per session
CREATE OR REPLACE VIEW v_training_latest_progress AS
SELECT
    s.session_id,
    s.user_id,
    s.status,
    s.current_round_no,
    ks.round_no AS latest_kt_round_no,
    ks.k1, ks.k2, ks.k3, ks.k4, ks.k5, ks.k6, ks.k7, ks.k8,
    ns.round_no AS latest_plot_round_no,
    ns.credibility, ns.accuracy, ns.public_panic, ns.source_safety, ns.editor_trust, ns.actionability
FROM training_sessions s
LEFT JOIN LATERAL (
    SELECT *
    FROM kt_state_snapshots x
    WHERE x.session_id = s.session_id
    ORDER BY x.round_no DESC
    LIMIT 1
) ks ON TRUE
LEFT JOIN LATERAL (
    SELECT *
    FROM narrative_state_snapshots y
    WHERE y.session_id = s.session_id
    ORDER BY y.round_no DESC
    LIMIT 1
) ns ON TRUE;

COMMIT;
