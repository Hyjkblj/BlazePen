import { beforeEach, describe, expect, it, vi } from 'vitest';
import httpClient, { getErrorData, getErrorStatus } from '@/services/httpClient';
import {
  getTrainingDiagnostics,
  getNextTrainingScenario,
  getTrainingProgress,
  getTrainingReport,
  getTrainingSessionSummary,
  initTraining,
  submitTrainingRound,
} from './trainingApi';

vi.mock('@/services/httpClient', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorData: vi.fn(),
  getErrorStatus: vi.fn(),
  unwrapApiData: vi.fn((value: unknown) => value),
}));

describe('trainingApi', () => {
  beforeEach(() => {
    vi.mocked(httpClient.post).mockReset();
    vi.mocked(httpClient.get).mockReset();
    vi.mocked(getErrorData).mockReset();
    vi.mocked(getErrorStatus).mockReset();
  });

  it('normalizes init request payloads and returns a training-only read model', async () => {
    vi.mocked(httpClient.post).mockResolvedValueOnce({
      session_id: 'training-session-1',
      status: 'active',
      round_no: 0,
      k_state: {
        K1: '0.45',
      },
      s_state: {
        source_safety: 0.9,
      },
      next_scenario: {
        id: 'scenario-1',
        title: 'Initial Briefing',
      },
    });

    await expect(
      initTraining({
        userId: 'user-1',
        characterId: '12',
        trainingMode: 'self_paced',
        playerProfile: {
          name: 'Reporter',
        },
      })
    ).resolves.toMatchObject({
      sessionId: 'training-session-1',
      trainingMode: 'self-paced',
      status: 'active',
      roundNo: 0,
      runtimeState: {
        currentSceneId: 'scenario-1',
        kState: {
          K1: 0.45,
        },
        sState: {
          source_safety: 0.9,
        },
      },
    });

    expect(httpClient.post).toHaveBeenCalledWith(
      '/v1/training/init',
      {
        user_id: 'user-1',
        character_id: 12,
        training_mode: 'self-paced',
        player_profile: {
          name: 'Reporter',
          gender: null,
          identity: null,
          age: null,
        },
      },
      { timeout: 60000 }
    );
  });

  it('rejects invalid characterId before calling the training init API', async () => {
    await expect(
      initTraining({
        userId: 'user-1',
        characterId: 'character-abc',
      })
    ).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      message: 'characterId must be a positive integer when initializing training.',
    });

    expect(httpClient.post).not.toHaveBeenCalled();
  });

  it('rejects an unsupported explicit training mode before calling the training init API', async () => {
    await expect(
      initTraining({
        userId: 'user-1',
        trainingMode: 'story' as never,
      })
    ).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      message: 'Unsupported training mode in request: story.',
    });

    expect(httpClient.post).not.toHaveBeenCalled();
  });

  it.each([
    ['TRAINING_SESSION_NOT_FOUND', 404, () => getNextTrainingScenario({ sessionId: 'session-missing' })],
    ['TRAINING_SESSION_COMPLETED', 400, () => getTrainingProgress('session-completed')],
    ['TRAINING_SESSION_RECOVERY_STATE_CORRUPTED', 409, () => getTrainingSessionSummary('session-broken')],
    [
      'TRAINING_ROUND_DUPLICATE',
      400,
      () =>
        submitTrainingRound({
          sessionId: 'session-1',
          scenarioId: 'scenario-1',
          userInput: 'submit choice',
        }),
    ],
  ] as const)(
    'preserves backend training error code %s',
    async (backendErrorCode, status, executeRequest) => {
      const requestError = new Error(`backend returned ${backendErrorCode}`);

      if (
        backendErrorCode === 'TRAINING_SESSION_COMPLETED' ||
        backendErrorCode === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED'
      ) {
        vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
      } else {
        vi.mocked(httpClient.post).mockRejectedValueOnce(requestError);
      }

      vi.mocked(getErrorStatus).mockReturnValueOnce(status);
      vi.mocked(getErrorData).mockReturnValueOnce({
        message: `${backendErrorCode} message`,
        error: {
          code: backendErrorCode,
        },
      });

      await expect(executeRequest()).rejects.toMatchObject({
        code: backendErrorCode,
        message: `${backendErrorCode} message`,
        status,
      });
    }
  );

  it('guards against invalid responses that omit sessionId', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      status: 'active',
      round_no: 3,
      total_rounds: 6,
    });

    await expect(getTrainingProgress('session-1')).rejects.toMatchObject({
      code: 'INVALID_RESPONSE',
      message: 'Missing sessionId in training progress response.',
    });
  });

  it('normalizes the training session summary restore payload', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      session_id: 'training-session-7',
      status: 'in_progress',
      training_mode: 'adaptive',
      current_round_no: 2,
      total_rounds: 5,
      progress_anchor: {
        current_round_no: 2,
        total_rounds: 5,
        completed_rounds: 2,
        remaining_rounds: 3,
        progress_percent: 0.4,
        next_round_no: 3,
      },
      runtime_state: {
        current_round_no: 2,
        current_scene_id: 'scenario-2',
      },
      resumable_scenario: {
        id: 'scenario-2',
        title: 'Follow-up interview',
      },
      scenario_candidates: [
        {
          id: 'scenario-2',
          title: 'Follow-up interview',
        },
      ],
      can_resume: true,
      is_completed: false,
      updated_at: '2026-03-20T09:00:00Z',
    });

    await expect(getTrainingSessionSummary('training-session-7')).resolves.toMatchObject({
      sessionId: 'training-session-7',
      trainingMode: 'adaptive',
      roundNo: 2,
      totalRounds: 5,
      progressAnchor: {
        roundNo: 2,
        progressPercent: 40,
        nextRoundNo: 3,
      },
      resumableScenario: {
        id: 'scenario-2',
      },
      scenarioCandidates: [{ id: 'scenario-2' }],
      canResume: true,
    });

    expect(httpClient.get).toHaveBeenCalledWith('/v1/training/sessions/training-session-7', {
      timeout: 30000,
    });
  });

  it('fails fast when the backend returns a legacy response training mode', async () => {
    vi.mocked(httpClient.post).mockResolvedValueOnce({
      session_id: 'training-session-1',
      status: 'active',
      round_no: 0,
      next_scenario: {
        id: 'scenario-1',
        title: 'Initial Briefing',
        recommendation: {
          mode: 'self_paced',
        },
      },
    });

    await expect(
      initTraining({
        userId: 'user-1',
        trainingMode: 'guided',
      })
    ).rejects.toMatchObject({
      code: 'INVALID_RESPONSE',
      message: 'Unsupported training mode in response at recommendation.mode.',
    });
  });

  it('normalizes the training report read model', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      session_id: 'training-session-report',
      status: 'completed',
      rounds: 3,
      improvement: '0.32',
      summary: {
        weighted_score_final: '0.76',
        review_suggestions: ['优先补练来源保护'],
      },
      ability_radar: [
        {
          code: 'K1',
          initial: 0.2,
          final: 0.6,
          delta: 0.4,
          is_highest_gain: true,
        },
      ],
      growth_curve: [
        {
          round_no: 0,
          scenario_title: '初始状态',
          weighted_k_score: 0.2,
        },
      ],
      history: [
        {
          round_no: 1,
          scenario_id: 'scenario-1',
          user_input: 'Protect the source',
        },
      ],
    });

    await expect(getTrainingReport('training-session-report')).resolves.toMatchObject({
      sessionId: 'training-session-report',
      status: 'completed',
      improvement: 0.32,
      summary: {
        weightedScoreFinal: 0.76,
        reviewSuggestions: ['优先补练来源保护'],
      },
      abilityRadar: [
        {
          code: 'K1',
          delta: 0.4,
          isHighestGain: true,
        },
      ],
      growthCurve: [
        {
          roundNo: 0,
          scenarioTitle: '初始状态',
        },
      ],
      history: [
        {
          roundNo: 1,
          scenarioId: 'scenario-1',
          userInput: 'Protect the source',
        },
      ],
    });

    expect(httpClient.get).toHaveBeenCalledWith('/v1/training/report/training-session-report', {
      timeout: 30000,
    });
  });

  it('normalizes the training diagnostics read model', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      session_id: 'training-session-diagnostics',
      status: 'completed',
      round_no: 3,
      summary: {
        total_recommendation_logs: 2,
        risk_flag_counts: [
          {
            code: 'source_exposure_risk',
            count: 1,
          },
        ],
      },
      recommendation_logs: [
        {
          round_no: 1,
          training_mode: 'guided',
          selection_source: 'candidate_pool',
          selected_scenario_id: 'scenario-1',
        },
      ],
      kt_observations: [
        {
          scenario_id: 'scenario-1',
          scenario_title: 'Initial Briefing',
          training_mode: 'guided',
          round_no: 1,
          observation_summary: 'Need stronger verification.',
        },
      ],
    });

    await expect(getTrainingDiagnostics('training-session-diagnostics')).resolves.toMatchObject({
      sessionId: 'training-session-diagnostics',
      status: 'completed',
      roundNo: 3,
      summary: {
        totalRecommendationLogs: 2,
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
          selectedScenarioId: 'scenario-1',
        },
      ],
      ktObservations: [
        {
          scenarioId: 'scenario-1',
          scenarioTitle: 'Initial Briefing',
          trainingMode: 'guided',
          roundNo: 1,
          observationSummary: 'Need stronger verification.',
        },
      ],
    });

    expect(httpClient.get).toHaveBeenCalledWith(
      '/v1/training/diagnostics/training-session-diagnostics',
      {
        timeout: 30000,
      }
    );
  });
});
