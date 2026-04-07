import { describe, expect, it } from 'vitest';
import {
  normalizeTrainingDiagnosticsPayload,
  normalizeTrainingInitPayload,
  normalizeTrainingMediaTaskView,
  normalizeTrainingMode,
  normalizeTrainingProgressPayload,
  normalizeTrainingReportPayload,
  normalizeTrainingRoundSubmitPayload,
  normalizeTrainingSessionSummaryPayload,
  resolveNarrativeForScenario,
} from './trainingSession';

describe('trainingSession normalizers', () => {
  it('normalizes request training mode aliases into the canonical frontend union', () => {
    expect(normalizeTrainingMode(undefined)).toBe('guided');
    expect(normalizeTrainingMode('self_paced')).toBe('self-paced');
    expect(normalizeTrainingMode('adaptive')).toBe('adaptive');
    expect(() => normalizeTrainingMode('unknown-mode')).toThrowError(
      'Unsupported training mode in request: unknown-mode.'
    );
  });

  it('builds a stable init read model from snake_case training payloads', () => {
    const result = normalizeTrainingInitPayload(
      {
        session_id: 'session-1',
        character_id: '12',
        status: 'active',
        round_no: '0',
        k_state: {
          K1: '0.75',
        },
        s_state: {
          editor_trust: 0.5,
        },
        player_profile: {
          name: 'Reporter',
          age: '26',
        },
        next_scenario: {
          id: 'scenario-1',
          title: 'Breaking News',
          decision_focus: 'Verify the source',
          options: [
            {
              id: 'opt-1',
              label: 'Hold publication',
              impact_hint: 'Protect source safety',
            },
          ],
          recommendation: {
            mode: 'self-paced',
            rank_score: '0.92',
            weakness_score: 0.4,
            state_boost_score: '0.3',
            reasons: ['source_safety'],
          },
        },
      },
      'self_paced'
    );

    expect(result).toEqual({
      sessionId: 'session-1',
      characterId: '12',
      trainingMode: 'self-paced',
      status: 'active',
      roundNo: 0,
      runtimeState: {
        currentRoundNo: 0,
        currentSceneId: 'scenario-1',
        kState: {
          K1: 0.75,
        },
        sState: {
          editor_trust: 0.5,
        },
        runtimeFlags: {
          panicTriggered: false,
          sourceExposed: false,
          editorLocked: false,
          highRiskPath: false,
        },
        stateBar: {
          editorTrust: 0,
          publicStability: 0,
          sourceSafety: 0,
        },
        playerProfile: {
          name: 'Reporter',
          gender: null,
          identity: null,
          age: 26,
        },
      },
      nextScenario: {
        id: 'scenario-1',
        title: 'Breaking News',
        eraDate: '',
        location: '',
        brief: '',
        mission: '',
        decisionFocus: 'Verify the source',
        targetSkills: [],
        riskTags: [],
        options: [
          {
            id: 'opt-1',
            label: 'Hold publication',
            impactHint: 'Protect source safety',
          },
        ],
        completionHint: '',
        recommendation: {
          mode: 'self-paced',
          rankScore: 0.92,
          weaknessScore: 0.4,
          stateBoostScore: 0.3,
          riskBoostScore: 0,
          phaseBoostScore: 0,
          reasons: ['source_safety'],
          rank: null,
        },
      },
      scenarioCandidates: [],
      scenarioSequence: [],
    });
  });

  it('normalizes scenario_sequence outlines from init payload', () => {
    const result = normalizeTrainingInitPayload(
      {
        session_id: 'session-seq',
        round_no: 0,
        scenario_sequence: [{ id: 'S1', title: 'One' }, { id: 'bad', title: '' }],
      },
      'guided'
    );
    expect(result.scenarioSequence).toEqual([
      { id: 'S1', title: 'One' },
      { id: 'bad', title: 'bad' },
    ]);
  });

  it('treats brief as the only canonical scenario summary field', () => {
    const result = normalizeTrainingInitPayload(
      {
        session_id: 'session-canonical-brief',
        status: 'active',
        round_no: 0,
        next_scenario: {
          id: 'scenario-canonical',
          title: 'Canonical Brief Scenario',
          brief: 'Use the canonical brief copy.',
        },
      },
      'guided'
    );

    expect(result.nextScenario).toMatchObject({
      id: 'scenario-canonical',
      brief: 'Use the canonical brief copy.',
    });
  });

  it('fails fast when the backend returns a non-canonical response training mode', () => {
    expect(() =>
      normalizeTrainingRoundSubmitPayload({
        session_id: 'session-2',
        round_no: 2,
        evaluation: {},
        decision_context: {
          mode: 'self_paced',
          selection_source: 'recommendation',
          selected_scenario_id: 'scenario-2',
        },
      })
    ).toThrowError('Unsupported training mode in response at decision_context.mode.');
  });

  it('keeps submit and progress state under runtimeState instead of exposing duplicate snake_case fields', () => {
    const submitResult = normalizeTrainingRoundSubmitPayload({
      session_id: 'session-2',
      round_no: 2,
      k_state: {
        K2: '0.61',
      },
      s_state: {
        source_safety: '0.88',
      },
      evaluation: {
        llm_model: 'rules_v2',
        confidence: '0.81',
        skill_delta: {
          K2: '0.11',
        },
        s_delta: {
          source_safety: '0.05',
        },
        evidence: ['confirmed timeline'],
      },
      decision_context: {
        mode: 'guided',
        selection_source: 'recommendation',
        selected_scenario_id: 'scenario-2',
      },
      consequence_events: [
        {
          event_type: 'source_warning',
          summary: 'Source risk increased',
          severity: 'high',
          round_no: '2',
          payload: {
            channel: 'mailbox',
          },
        },
      ],
      media_tasks: [
        {
          task_id: 'task-image-1',
          task_type: 'image',
          status: 'pending',
        },
      ],
      is_completed: false,
    });

    expect(submitResult.runtimeState.currentSceneId).toBe('scenario-2');
    expect(submitResult.runtimeState.kState).toEqual({ K2: 0.61 });
    expect(submitResult.evaluation.stateDelta).toEqual({ source_safety: 0.05 });
    expect(submitResult.consequenceEvents).toEqual([
      {
        eventType: 'source_warning',
        label: '',
        summary: 'Source risk increased',
        severity: 'high',
        roundNo: 2,
        relatedFlag: null,
        stateBar: null,
        payload: {
          channel: 'mailbox',
        },
      },
    ]);
    expect(submitResult.mediaTasks).toEqual([
      {
        taskId: 'task-image-1',
        taskType: 'image',
        status: 'pending',
      },
    ]);

    const progressResult = normalizeTrainingProgressPayload({
      session_id: 'session-2',
      character_id: '24',
      status: 'active',
      round_no: 2,
      total_rounds: '6',
      runtime_state: {
        current_round_no: '2',
        current_scene_id: 'scenario-2',
        k_state: {
          K2: '0.61',
        },
        s_state: {
          source_safety: '0.88',
        },
        runtime_flags: {
          source_exposed: true,
        },
      },
    });

    expect(progressResult).toEqual({
      sessionId: 'session-2',
      characterId: '24',
      status: 'active',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: {
        currentRoundNo: 2,
        currentSceneId: 'scenario-2',
        kState: {
          K2: 0.61,
        },
        sState: {
          source_safety: 0.88,
        },
        runtimeFlags: {
          panicTriggered: false,
          sourceExposed: true,
          editorLocked: false,
          highRiskPath: false,
        },
        stateBar: {
          editorTrust: 0,
          publicStability: 0,
          sourceSafety: 0,
        },
        playerProfile: null,
      },
      decisionContext: null,
      consequenceEvents: [],
      ending: null,
    });
  });

  it('maps raw media task payloads into stable UI-facing fields', () => {
    const taskView = normalizeTrainingMediaTaskView({
      taskId: 'task-1',
      sessionId: 'session-1',
      roundNo: 2,
      taskType: 'image',
      status: 'succeeded',
      result: {
        image_urls: ['https://example.com/image-a.png'],
      },
      error: null,
      createdAt: '2026-03-25T12:00:00Z',
      updatedAt: '2026-03-25T12:00:00Z',
      startedAt: null,
      finishedAt: null,
    });

    expect(taskView).toMatchObject({
      taskId: 'task-1',
      previewUrl: 'https://example.com/image-a.png',
      audioUrl: null,
      generatedText: null,
      errorMessage: null,
    });
  });

  it('normalizes the training session summary into a resumable frontend read model', () => {
    const summaryResult = normalizeTrainingSessionSummaryPayload({
      session_id: 'session-restore',
      character_id: '42',
      status: 'in_progress',
      training_mode: 'guided',
      current_round_no: '2',
      total_rounds: '6',
      k_state: {
        K2: '0.61',
      },
      s_state: {
        source_safety: '0.88',
      },
      progress_anchor: {
        current_round_no: '2',
        total_rounds: '6',
        completed_rounds: '2',
        remaining_rounds: '4',
        progress_percent: '0.3333',
        next_round_no: '3',
      },
      resumable_scenario: {
        id: 'scenario-2',
        title: 'Investigate the leak',
      },
      scenario_candidates: [
        {
          id: 'scenario-2',
          title: 'Investigate the leak',
        },
      ],
      runtime_state: {
        current_round_no: '2',
        current_scene_id: 'scenario-2',
      },
      can_resume: true,
      is_completed: false,
      updated_at: '2026-03-20T09:00:00Z',
    });

    expect(summaryResult).toMatchObject({
      sessionId: 'session-restore',
      characterId: '42',
      trainingMode: 'guided',
      status: 'in_progress',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: {
        currentRoundNo: 2,
        currentSceneId: 'scenario-2',
        kState: {
          K2: 0.61,
        },
        sState: {
          source_safety: 0.88,
        },
        runtimeFlags: {
          panicTriggered: false,
          sourceExposed: false,
          editorLocked: false,
          highRiskPath: false,
        },
        stateBar: {
          editorTrust: 0,
          publicStability: 0,
          sourceSafety: 0,
        },
        playerProfile: null,
      },
      progressAnchor: {
        roundNo: 2,
        totalRounds: 6,
        completedRounds: 2,
        remainingRounds: 4,
        nextRoundNo: 3,
      },
      resumableScenario: {
        id: 'scenario-2',
        title: 'Investigate the leak',
        eraDate: '',
        location: '',
        brief: '',
        mission: '',
        decisionFocus: '',
        targetSkills: [],
        riskTags: [],
        options: [],
        completionHint: '',
        recommendation: null,
      },
      scenarioCandidates: [
        {
          id: 'scenario-2',
          title: 'Investigate the leak',
          eraDate: '',
          location: '',
          brief: '',
          mission: '',
          decisionFocus: '',
          targetSkills: [],
          riskTags: [],
          options: [],
          completionHint: '',
          recommendation: null,
        },
      ],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: '2026-03-20T09:00:00Z',
      endTime: null,
    });
    expect(summaryResult.progressAnchor.progressPercent).toBeCloseTo(33.33, 2);
  });

  it('normalizes the training report payload into a display-first read model', () => {
    const reportResult = normalizeTrainingReportPayload({
      session_id: 'session-report',
      character_id: 52,
      status: 'completed',
      rounds: '3',
      improvement: '0.27',
      summary: {
        weighted_score_final: '0.76',
        strongest_improved_skill_code: 'K1',
        risk_flag_counts: [
          {
            code: 'source_exposure_risk',
            count: '1',
          },
        ],
        branch_transitions: [
          {
            source_scenario_id: 'S1',
            target_scenario_id: 'S2',
            count: '1',
            triggered_flags: ['source_warning'],
          },
        ],
        review_suggestions: ['优先补练来源保护'],
      },
      ability_radar: [
        {
          code: 'K1',
          initial: '0.2',
          final: '0.55',
          delta: '0.35',
          is_highest_gain: true,
        },
      ],
      growth_curve: [
        {
          round_no: 0,
          scenario_title: '初始状态',
          weighted_k_score: '0.2',
        },
      ],
      round_snapshots: [
        {
          round_no: 1,
          scenario_id: 'S1',
          scenario_title: '场景一',
          risk_flags: ['source_exposure_risk'],
          is_high_risk: true,
          branch_transition: {
            source_scenario_id: 'S0',
            target_scenario_id: 'S1',
            transition_type: 'branch',
            reason: 'source_warning',
          },
        },
      ],
      history: [
        {
          round_no: 1,
          scenario_id: 'S1',
          user_input: 'Protect the source',
          decision_context: {
            mode: 'guided',
            selection_source: 'manual',
            selected_scenario_id: 'S1',
          },
        },
      ],
    });

    expect(reportResult).toMatchObject({
      sessionId: 'session-report',
      characterId: '52',
      status: 'completed',
      rounds: 3,
      improvement: 0.27,
      summary: {
        weightedScoreFinal: 0.76,
        strongestImprovedSkillCode: 'K1',
        riskFlagCounts: [
          {
            code: 'source_exposure_risk',
            count: 1,
          },
        ],
        branchTransitions: [
          {
            sourceScenarioId: 'S1',
            targetScenarioId: 'S2',
            count: 1,
            triggeredFlags: ['source_warning'],
          },
        ],
        reviewSuggestions: ['优先补练来源保护'],
      },
      abilityRadar: [
        {
          code: 'K1',
          delta: 0.35,
          isHighestGain: true,
        },
      ],
      growthCurve: [
        {
          roundNo: 0,
          scenarioTitle: '初始状态',
        },
      ],
      roundSnapshots: [
        {
          roundNo: 1,
          scenarioId: 'S1',
          scenarioTitle: '场景一',
          riskFlags: ['source_exposure_risk'],
          isHighRisk: true,
          branchTransition: {
            source_scenario_id: 'S0',
            target_scenario_id: 'S1',
            transition_type: 'branch',
            reason: 'source_warning',
          },
        },
      ],
      history: [
        {
          roundNo: 1,
          scenarioId: 'S1',
          userInput: 'Protect the source',
          decisionContext: {
            selectionSource: 'manual',
            selectedScenarioId: 'S1',
          },
        },
      ],
    });
  });

  it('normalizes the training diagnostics payload into an explainable read model', () => {
    const diagnosticsResult = normalizeTrainingDiagnosticsPayload({
      session_id: 'session-diagnostics',
      character_id: '61',
      status: 'completed',
      round_no: '3',
      summary: {
        total_recommendation_logs: '2',
        recommended_vs_selected_mismatch_count: '1',
        risk_flag_counts: [
          {
            code: 'source_exposure_risk',
            count: '1',
          },
        ],
      },
      recommendation_logs: [
        {
          round_no: 1,
          training_mode: 'guided',
          selection_source: 'candidate_pool',
          selected_scenario_id: 'S1',
        },
      ],
      kt_observations: [
        {
          scenario_id: 'S1',
          scenario_title: 'Initial Briefing',
          training_mode: 'guided',
          round_no: 1,
          observation_summary: 'Need stronger verification.',
        },
      ],
      audit_events: [
        {
          event_type: 'decision_trace',
          round_no: 1,
          timestamp: '2026-03-20T09:00:00Z',
        },
      ],
    });

    expect(diagnosticsResult).toMatchObject({
      sessionId: 'session-diagnostics',
      characterId: '61',
      status: 'completed',
      roundNo: 3,
      summary: {
        totalRecommendationLogs: 2,
        recommendedVsSelectedMismatchCount: 1,
        riskFlagCounts: [
          {
            code: 'source_exposure_risk',
            count: 1,
          },
        ],
      },
      recommendationLogs: [
        {
          roundNo: 1,
          trainingMode: 'guided',
          selectionSource: 'candidate_pool',
          selectedScenarioId: 'S1',
        },
      ],
      ktObservations: [
        {
          scenarioId: 'S1',
          scenarioTitle: 'Initial Briefing',
          observationSummary: 'Need stronger verification.',
        },
      ],
      auditEvents: [
        {
          eventType: 'decision_trace',
          roundNo: 1,
          timestamp: '2026-03-20T09:00:00Z',
        },
      ],
      ending: null,
    });
  });
});

describe('resolveNarrativeForScenario', () => {
  const v2Payload = {
    version: 'training_story_script_v2',
    narratives: {
      'major-1': {
        monologue: '独白内容',
        dialogue: [{ speaker: '记者', content: '你好' }],
        bridge_summary: '承接摘要',
        options_narrative: {
          'opt-1': { option_id: 'opt-1', narrative_label: '选项一', impact_hint: '影响提示' },
        },
      },
    },
  };

  const v1Payload = {
    scenes: [
      {
        scene_id: 'major-1',
        monologue: 'v1 独白',
        dialogue: [{ speaker: '编辑', content: '注意核实' }],
        bridge_summary: 'v1 摘要',
        options_narrative: {},
      },
    ],
  };

  it('reads from narratives dict when payload is v2 (Requirements 6.1)', () => {
    const result = resolveNarrativeForScenario(v2Payload, 'major-1');
    expect(result).not.toBeNull();
    expect(result?.monologue).toBe('独白内容');
    expect(result?.dialogue).toEqual([{ speaker: '记者', content: '你好' }]);
    expect(result?.bridge_summary).toBe('承接摘要');
    expect(result?.options_narrative['opt-1']).toMatchObject({ narrative_label: '选项一' });
  });

  it('falls back to scenes[].scene_id lookup for v1 payload (Requirements 6.2)', () => {
    const result = resolveNarrativeForScenario(v1Payload, 'major-1');
    expect(result).not.toBeNull();
    expect(result?.monologue).toBe('v1 独白');
  });

  it('matches v1 scene by prefix for micro scenarios (Requirements 6.2)', () => {
    const result = resolveNarrativeForScenario(v1Payload, 'major-1_micro_1_1_suffix');
    expect(result).not.toBeNull();
    expect(result?.monologue).toBe('v1 独白');
  });

  it('returns null when scenarioId is not found in v2 payload (Requirements 6.4)', () => {
    const result = resolveNarrativeForScenario(v2Payload, 'nonexistent-scenario');
    expect(result).toBeNull();
  });

  it('returns null when scenarioId is not found in v1 payload (Requirements 6.4)', () => {
    const result = resolveNarrativeForScenario(v1Payload, 'nonexistent-scenario');
    expect(result).toBeNull();
  });

  it('returns null for null/undefined payload without throwing (Requirements 6.4)', () => {
    expect(resolveNarrativeForScenario(null, 'major-1')).toBeNull();
    expect(resolveNarrativeForScenario(undefined, 'major-1')).toBeNull();
    expect(resolveNarrativeForScenario({}, 'major-1')).toBeNull();
  });

  it('returns null for malformed payload without throwing (Requirements 6.4)', () => {
    expect(resolveNarrativeForScenario('not-an-object', 'major-1')).toBeNull();
    expect(resolveNarrativeForScenario(42, 'major-1')).toBeNull();
    expect(resolveNarrativeForScenario({ version: 'training_story_script_v2' }, 'major-1')).toBeNull();
  });
});
