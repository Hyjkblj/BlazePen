import { beforeEach, describe, expect, it, vi } from 'vitest';
import httpClient, { getErrorData, getErrorStatus } from '@/services/httpClient';
import {
  checkEnding,
  getStoryEndingSummary,
  getStorySessionHistory,
  getStorySessionSnapshot,
  processGameInput,
} from './gameApi';

vi.mock('@/services/httpClient', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorData: vi.fn(),
  getErrorStatus: vi.fn(),
  unwrapApiData: vi.fn((value: unknown) => value),
}));

describe('gameApi story session error mapping', () => {
  beforeEach(() => {
    vi.mocked(httpClient.post).mockReset();
    vi.mocked(httpClient.get).mockReset();
    vi.mocked(getErrorData).mockReset();
    vi.mocked(getErrorStatus).mockReset();
  });

  it.each([
    ['STORY_SESSION_NOT_FOUND', 404],
    ['STORY_SESSION_EXPIRED', 410],
    ['STORY_SESSION_RESTORE_FAILED', 400],
  ] as const)(
    'preserves backend story session error code %s during turn submission',
    async (backendErrorCode, status) => {
      const requestError = new Error(`backend returned ${backendErrorCode}`);
      vi.mocked(httpClient.post).mockRejectedValueOnce(requestError);
      vi.mocked(getErrorStatus).mockReturnValueOnce(status);
      vi.mocked(getErrorData).mockReturnValueOnce({
        message: `${backendErrorCode} message`,
        error: {
          code: backendErrorCode,
        },
      });

      await expect(
        processGameInput({
          threadId: 'thread-1',
          userInput: 'option:1',
          characterId: 'character-1',
        })
      ).rejects.toMatchObject({
          code: backendErrorCode,
          message: `${backendErrorCode} message`,
          status,
        });
    }
  );

  it('preserves backend story session restore failure during snapshot restore', async () => {
    const requestError = new Error('snapshot restore failed');
    vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(400);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'Snapshot restore failed.',
      error: {
        code: 'STORY_SESSION_RESTORE_FAILED',
      },
    });

    await expect(getStorySessionSnapshot('thread-1')).rejects.toMatchObject({
        code: 'STORY_SESSION_RESTORE_FAILED',
        message: 'Snapshot restore failed.',
        status: 400,
      });
  });

  it('preserves backend story session not found during canonical ending summary lookup', async () => {
    const requestError = new Error('ending not found');
    vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(404);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'Ending summary missing.',
      error: {
        code: 'STORY_SESSION_NOT_FOUND',
      },
    });

    await expect(getStoryEndingSummary('thread-missing')).rejects.toMatchObject({
      code: 'STORY_SESSION_NOT_FOUND',
      message: 'Ending summary missing.',
      status: 404,
    });
  });

  it('preserves backend story session not found during canonical story history lookup', async () => {
    const requestError = new Error('history not found');
    vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(404);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'Story history missing.',
      error: {
        code: 'STORY_SESSION_NOT_FOUND',
      },
    });

    await expect(getStorySessionHistory('thread-missing')).rejects.toMatchObject({
      code: 'STORY_SESSION_NOT_FOUND',
      message: 'Story history missing.',
      status: 404,
    });
  });

  it('maps the canonical ending summary route into the legacy checkEnding adapter shape', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      thread_id: 'thread-ended',
      status: 'completed',
      round_no: 6,
      has_ending: true,
      ending: {
        type: 'good_ending',
        description: 'A warm ending.',
        scene: 'study_room',
        event_title: 'Final Promise',
        key_states: {
          favorability: 88,
          trust: '76',
          hostility: 12,
          dependence: 40,
        },
      },
      updated_at: '2026-03-20T10:00:00Z',
      expires_at: '2026-03-20T10:30:00Z',
    });

    await expect(checkEnding('thread-ended')).resolves.toEqual({
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm ending.',
        favorability: 88,
        trust: 76,
        hostility: 12,
      },
    });
    expect(httpClient.get).toHaveBeenCalledWith('/v1/game/sessions/thread-ended/ending', {
      timeout: 30000,
    });
  });

  it('normalizes the canonical story history route into a frontend read model', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      thread_id: 'thread-live',
      status: 'completed',
      current_round_no: 4,
      latest_scene: 'study_room',
      updated_at: '2026-03-20T12:00:00Z',
      expires_at: '2026-03-20T12:30:00Z',
      history: [
        {
          round_no: 1,
          status: 'in_progress',
          scene: 'study_room',
          event_title: 'First Meeting',
          character_dialogue: 'Nice to meet you.',
          user_action: {
            kind: 'option',
            summary: 'Wave back',
            option_index: 0,
            option_text: 'Wave back',
            option_type: 'action',
          },
          state_summary: {
            changes: {
              trust: '10',
            },
            current_states: {
              trust: 60,
              hostility: '12',
            },
          },
          is_event_finished: false,
          is_game_finished: false,
          created_at: '2026-03-20T11:58:00Z',
        },
      ],
    });

    await expect(getStorySessionHistory('thread-live')).resolves.toEqual({
      threadId: 'thread-live',
      status: 'completed',
      currentRoundNo: 4,
      latestSceneId: 'study_room',
      updatedAt: '2026-03-20T12:00:00Z',
      expiresAt: '2026-03-20T12:30:00Z',
      history: [
        {
          roundNo: 1,
          status: 'in_progress',
          sceneId: 'study_room',
          eventTitle: 'First Meeting',
          characterDialogue: 'Nice to meet you.',
          userAction: {
            kind: 'option',
            summary: 'Wave back',
            rawInput: null,
            optionIndex: 0,
            optionText: 'Wave back',
            optionType: 'action',
          },
          stateSummary: {
            changes: {
              trust: 10,
            },
            currentStates: {
              trust: 60,
              hostility: 12,
            },
          },
          isEventFinished: false,
          isGameFinished: false,
          createdAt: '2026-03-20T11:58:00Z',
        },
      ],
    });
    expect(httpClient.get).toHaveBeenCalledWith('/v1/game/sessions/thread-live/history', {
      timeout: 30000,
    });
  });
});
