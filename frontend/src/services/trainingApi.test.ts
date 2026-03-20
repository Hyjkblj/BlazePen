import { beforeEach, describe, expect, it, vi } from 'vitest';
import httpClient, { getErrorData, getErrorStatus } from '@/services/httpClient';
import {
  getNextTrainingScenario,
  getTrainingProgress,
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

      if (backendErrorCode === 'TRAINING_SESSION_COMPLETED') {
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
});
