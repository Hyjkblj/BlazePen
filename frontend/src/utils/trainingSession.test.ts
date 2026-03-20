import { describe, expect, it } from 'vitest';
import {
  normalizeTrainingInitPayload,
  normalizeTrainingMode,
  normalizeTrainingProgressPayload,
  normalizeTrainingRoundSubmitPayload,
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
        briefing: '',
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

    const progressResult = normalizeTrainingProgressPayload({
      session_id: 'session-2',
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
    });
  });
});
